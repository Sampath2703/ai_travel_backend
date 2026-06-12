import os
import json
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from tavily import TavilyClient
from langchain_groq import ChatGroq
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

app = FastAPI()

# Enable CORS for cross-domain communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fetch Environment Variables
tavily_api_key = os.getenv("TAVILY_API_KEY")
rapid_api_key = os.getenv("RAPID_API_KEY")
weather_api = os.getenv("WEATHER_API_KEY")
unsplash_key = os.getenv("UNSPLASH_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

tavily = TavilyClient(api_key=tavily_api_key)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=groq_api_key
)


@tool
def weather_tool(city: str):
    """
    Get current weather information for a city.
    """
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": weather_api,
        "units": "metric"
    }
    try:
        res = requests.get(url, params=params)
        output = res.json() if res.status_code == 200 else {"info": f"Weather data for {city} is unavailable."}
        return json.dumps(output)
    except Exception as e:
        return json.dumps({"info": f"Weather data error: {str(e)}"})


@tool
def web_tool(query: str):
    """
    Search travel-related information from the web.
    Use this to find real-world schedules if transport_tool doesn't yield live results.
    """
    try:
        results = tavily.search(query=query, max_results=5)
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def budget_tool(data: str):
    """
    Calculate travel budget breakdown.
    Input format: budget,days (example: 20000,5)
    """
    try:
        budget, days = data.split(",")
        budget = float(budget)
        days = int(days)

        breakdown = {
            "total": budget,
            "per_day": budget / days,
            "stay": budget * 0.4,
            "food": budget * 0.3,
            "travel": budget * 0.2,
            "activities": budget * 0.1
        }
        return json.dumps(breakdown)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def transport_tool(data: str):
    """
    Get live transport details between cities.
    Format: mode,origin,destination
    Example: Flight,Delhi,Mumbai
    """
    try:
        mode, origin, destination = data.split(",")
        mode = mode.strip().lower()
        origin = origin.strip().lower()
        destination = destination.strip().lower()

        headers = {"X-RapidAPI-Key": rapid_api_key}

        # Main Station Hub Mapping
        station_map = {
            "delhi": {"flight": "DEL", "train": "NDLS"},
            "mumbai": {"flight": "BOM", "train": "CSMT"},
            "bangalore": {"flight": "BLR", "train": "SBC"},
            "bengaluru": {"flight": "BLR", "train": "SBC"},
            "goa": {"flight": "GOI", "train": "MAO"},
            "hyderabad": {"flight": "HYD", "train": "SC"},
            "chennai": {"flight": "MAA", "train": "MAS"},
            "kolkata": {"flight": "CCU", "train": "HWH"},
            "pune": {"flight": "PNQ", "train": "PUNE"}
        }

        # --- Flight Mode Handling ---
        if mode == "flight":
            headers["X-RapidAPI-Host"] = "aerodatabox.p.rapidapi.com"
            url = "https://aerodatabox.p.rapidapi.com/flights/search/routes"
            
            dep = station_map.get(origin, {}).get("flight", origin[:3].upper())
            arr = station_map.get(destination, {}).get("flight", destination[:3].upper())
            
            params = {"departureAirport": dep, "arrivalAirport": arr}
            res = requests.get(url, headers=headers, params=params)
            output = res.json() if res.status_code == 200 else {"info": "No live flight schedules returned."}
            return json.dumps(output)

        # --- Train Mode Handling ---
        elif mode == "train":
            headers["X-RapidAPI-Host"] = "indian-railway-v3.p.rapidapi.com"
            url = "https://indian-railway-v3.p.rapidapi.com/trains/betweenStations"
            
            # For custom destinations outside main hubs (like Arunachalam), trigger web search safely
            if origin not in station_map or destination not in station_map:
                return json.dumps({"info": f"Exact station codes for {origin} or {destination} are unmapped."})
                
            dep = station_map[origin]["train"]
            arr = station_map[destination]["train"]
            
            params = {"fromStationCode": dep, "toStationCode": arr}
            res = requests.get(url, headers=headers, params=params)
            output = res.json() if res.status_code == 200 else {"info": "No live trains found on this route."}
            return json.dumps(output)

        # --- Bus Mode Handling ---
        elif mode == "bus":
            headers["X-RapidAPI-Host"] = "distance-calculator8.p.rapidapi.com"
            url = "https://distance-calculator8.p.rapidapi.com/distance"
            params = {"origin": origin, "destination": destination}
            res = requests.get(url, headers=headers, params=params)
            output = res.json() if res.status_code == 200 else {"info": "Bus routing infrastructure missing."}
            return json.dumps(output)

        return json.dumps({"error": "Invalid transport mode requested."})
    except Exception as e:
        return json.dumps({"info": f"Live tracking details unavailable: {str(e)}"})


@tool
def image_tool(query: str):
    """
    Fetch travel-related images using Unsplash API.
    """
    if not unsplash_key:
        return json.dumps([])
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {unsplash_key}"}
    params = {"query": query, "per_page": 8}
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            data = res.json()
            urls = [img["urls"]["regular"] for img in data.get("results", []) if "urls" in img]
            return json.dumps(urls)
        return json.dumps([])
    except Exception:
        return json.dumps([])


# Agent creation with LangGraph React Architecture
agent = create_react_agent(
    model=llm,
    tools=[weather_tool, web_tool, budget_tool, transport_tool, image_tool],
    prompt="""
You are an expert AI Travel Planner.
When providing transport schedules, you must display the data explicitly.
- For Flights: Extract the operator/airline name, flight schedules, departure times, and arrival times.
- For Trains: Extract the specific train name, train number, and departure/arrival times.

CRITICAL REQUIREMENT: At the beginning of the itinerary, construct a clear Markdown Table containing the columns:
| Transport Name/Airline | Flight/Train Number | Departure Time | Arrival Time |

If the data from transport_tool returns an unmapped message, error, or empty responses, use web_tool immediately to search for actual real-world flight/train schedules or travel routes for that destination (e.g., search 'Schedules and options from Chennai to Arunachalam') and build the transit timetable from those online search results instead of omitting it.
"""
)


class TravelRequest(BaseModel):
    From: str
    To: str
    days: int
    budget: float
    trip_type: str
    Travel: str
    intrest: List[str]


@app.get("/")
def read_root():
    return {"status": "Backend running successfully"}


@app.post("/plan")
def plan_trip(req: TravelRequest):
    try:
        query = f"""
        Plan a {req.days}-day trip from {req.From} to {req.To}.
        Trip type: {req.trip_type}.
        Interests: {', '.join(req.intrest)}.
        Budget: {req.budget}.
        Transport: {req.Travel}.
        
        You must find the exact available schedules and timings for {req.Travel} options connecting {req.From} to {req.To} and put them in a table.
        """

        # Running LangGraph Flow
        result = agent.invoke({"messages": [HumanMessage(content=query)]})

        # Fetch Images
        interests_string = " ".join(req.intrest) if req.intrest else "tourism"
        combined_query = f"{req.To} {interests_string}"
        
        # Raw tool invocation returns a JSON string now, so we load it back to a python list
        try:
            fetched_images = json.loads(image_tool.invoke(combined_query))
        except Exception:
            fetched_images = []
            
        images = {"Gallery": fetched_images} if fetched_images else {}

        return {
            "response": result["messages"][-1].content,
            "images": images
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))