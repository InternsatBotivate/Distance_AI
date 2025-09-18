import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware # Import the CORS middleware
from agent import graph  # import your LangGraph graph

app = FastAPI(title="Diya Receptionist Bot")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}

# Request/Response models
class QueryRequest(BaseModel):
    message: str

class QueryResponse(BaseModel):
    reply: str

@app.post("/chat", response_model=QueryResponse)
def chat(req: QueryRequest):
    # Start graph execution with user message
    events = graph.stream({"messages": [("user", req.message)]}, config, stream_mode="values")

    reply = None
    for event in events:
        if "messages" in event:
            reply = event["messages"][-1].content

    return QueryResponse(reply=reply)
