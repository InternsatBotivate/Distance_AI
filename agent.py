import os
import uuid
import time
import math
import requests
from typing import TypedDict, Sequence, Dict, List, Annotated
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# from google_maps_api import geocode
from dotenv import load_dotenv

load_dotenv()

STATE_MAP = {
    "A.P": "Andhra Pradesh",
    "AP": "Andhra Pradesh",
    "C.G": "Chhattisgarh",
    "CG": "Chhattisgarh",
    "M.P": "Madhya Pradesh",
    "MP": "Madhya Pradesh",
    "T.N": "Tamil Nadu",
    "TN": "Tamil Nadu",
    "U.P": "Uttar Pradesh",
    "UP": "Uttar Pradesh",
    "K.A": "Karnataka",
    "KA": "Karnataka",
    "Orissa": "Odisha",
    # add more as needed
}


SYSTEM_MESSAGE = """
You are Diya, a helpful receptionist AI assistant.

Your task:
- Answer user queries about vendors/companies using the data provided in `state["companies"]`. 
- Each company in `state["companies"]` has the following fields:  
  - S. No.  
  - Vendor Name  
  - City  
  - State  
  - Address  
  - Latitude
  - Longitude
  
How to work:
1. Always use the companies in `state["companies"]`. Do not invent or use other companies.  
2. If asked for the closest company or vendor to a given location:  
   - Compare distances and return the closest company.   
   - Find the longitude and latitude user mentioned using the `get_location` tool if the address is not available or mentioned in `state["companies"]`.
   - Call the `get_distance` tool to calculate distances.  
   - Do not use `get_location` tool for the companies in `state["companies"]`.
3. If asked about a company's address, city, or state, fetch it directly from `state["companies"]`.  
4. Always introduce yourself as Diya in the first message.  
5. Do not ask the user to re-provide company data; you already have it in `state["companies"]`.  
6. Always prefer tool calls over vague explanations.  
7. If asked distance or coordinates from a new unkown address or place that not mentioned in the companies dataset, get the location for it.

Your output should either be:  
- A normal friendly message from Diya, or  
- A tool call (`get_location`, `get_distance`) only when needed.  

Never ignore the `companies` dataset. Never fabricate data.
Give quick and crisp replies. Do not ask follow up questions.
"""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    companies: List[Dict]


def is_in_india(lat: float, lon: float) -> bool:
    """Check if coordinates fall inside India's bounding box."""
    return 6 <= lat <= 38 and 68 <= lon <= 98


@tool
def get_distance(start: List[str], end: List[str]) -> float:
    """
    Calculate the distance between two locations using the formula.

    Args:
        start: [latitude, longitude] of the starting point as strings.
        end: [latitude, longitude] of the destination point as strings.

    Returns:
        Distance between the two locations in the chosen unit as a float in Kilometers.
    """
    # Convert to floats
    lat1, lon1 = map(float, start)
    lat2, lon2 = map(float, end)

    # Convert degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Radius of Earth
    r_km = 6371.0

    return c * r_km


@tool
def get_location(addresses: List[str]) -> Dict[str, List[str]]:
    """
    Given one or more address strings, fetch their corresponding geographic
    information.

    Args:
        addresses: Variable number of address strings in a list.

    Returns:
        Dict[str, List[str, str]]: A mapping where each input address maps to a
        list containing its latitude and longitude as strings.
    """
    geolocator = Nominatim(user_agent="diya_receptionist", timeout=10)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)  # throttle

    results: Dict[str, List[str]] = {}

    for address in addresses:
        coords = None
        for attempt in range(3):  # retry up to 3 times
            try:
                location = geocode(address)
                if (
                    location
                    and is_in_india(location.latitude, location.longitude)
                ):
                    coords = [str(location.latitude), str(location.longitude)]
                break
            except Exception as e:
                time.sleep(2)  # backoff before retry
                last_error = str(e)

        if coords:
            results[address] = coords
        else:
            results[address] = [
                "Not found",
                last_error if "last_error" in locals() else "Error",
            ]

    return results


tools = [get_location, get_distance]

llm = ChatOpenAI(model="gpt-5", api_key=os.getenv("OPENAI_API_KEY")).bind_tools(
    tools
)

system_message = SystemMessage(content=SYSTEM_MESSAGE)


def get_companies(state: AgentState) -> AgentState:
    response = requests.request("get", os.getenv("APPS_SCRIPT_URL"))
    state["companies"] = response.json()
    return state


def call_model(state: AgentState) -> AgentState:
    companies_text = "\n".join(
        [
            f"{c['S. No.']}. {c['Vendor Name']} |  {c['Vendor Name']}, {c['City']}, {STATE_MAP.get(c['State'], c['State'])} | {c['Address']}"
            for c in state.get("companies", [])
        ]
    )
    system_message.content += f"""
### Data
Here is the current list of companies:
{companies_text}
"""
    response = llm.invoke([system_message] + state["messages"])
    return {"messages": [response]}


tool_node = ToolNode(tools)

memory = MemorySaver()

graph = (
    StateGraph(AgentState)
    .add_node("fetch_data", get_companies)
    .add_node("model", call_model)  # Add model node
    .add_node("tools", tool_node)  # Add Tool node
    .add_edge("tools", "model")  # Connect tools to model
    .add_edge("fetch_data", "model")
    .add_conditional_edges("model", tools_condition)
    .set_entry_point("fetch_data")  # Set starting point
    .compile(checkpointer=memory)
)


if __name__ == "__main__":
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        user_input = input("You: ")
        if user_input == "q":
            print("Goodbye!")
            break

        for event in graph.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config,
            stream_mode="values",
        ):
            message = event["messages"][-1]
            if not isinstance(message, tuple):
                message.pretty_print()
