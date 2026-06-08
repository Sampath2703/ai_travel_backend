import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from tavily import TavilyClient
from langchain_groq import ChatGroq
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

app = FastAPI()

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
    return requests.get(url, params=params).json()


@tool
def web_tool(query: str):
    """
    Search travel-related information from the web.
    """
    return tavily.search(query=query, max_results=5)


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

        return {
            "total": budget,
            "per_day": budget / days,
            "stay": budget * 0.4,
            "food": budget * 0.3,
            "travel": budget * 0.2,
            "activities": budget * 0.1
        }
    except Exception as e:
        return {"error": str(e)}


@tool
def transport_tool(data: str):
    """
    Get live transport details.
    Format: mode,origin,destination
    Example: Flight,Delhi,Mumbai
    """
    try:
        mode, origin, destination = data.split(",")

        headers = {"X-RapidAPI-Key": rapid_api_key}

        if mode.lower() == "flight":
            headers["X-RapidAPI-Host"] = "aerodatabox.p.rapidapi.com"
            url = "https://aerodatabox.p.rapidapi.com/flights/search/routes"
            params = {
                "departureAirport": origin[:3].upper(),
                "arrivalAirport": destination[:3].upper()
            }
            return requests.get(url, headers=headers, params=params).json()

        elif mode.lower() == "train":
            headers["X-RapidAPI-Host"] = "indian-railway-v3.p.rapidapi.com"
            url = "https://indian-railway-v3.p.rapidapi.com/trains/betweenStations"
            params = {
                "fromStationCode": origin[:3].upper(),
                "toStationCode": destination[:3].upper()
            }
            return requests.get(url, headers=headers, params=params).json()

        elif mode.lower() == "bus":
            headers["X-RapidAPI-Host"] = "distance-calculator8.p.rapidapi.com"
            url = "https://distance-calculator8.p.rapidapi.com/distance"
            params = {"origin": origin, "destination": destination}
            return requests.get(url, headers=headers, params=params).json()

        return {"error": "Invalid mode"}

    except Exception as e:
        return {"error": str(e)}


@tool
def image_tool(query: str):
    """
    Fetch travel-related images using Unsplash API.
    """
    url = "https://api.unsplash.com/search/photos"
    headers = {
        "Authorization": f"Client-ID {unsplash_key}"
    }
    params = {
        "query": query,
        "per_page": 4
    }

    res = requests.get(url, headers=headers, params=params)
    data = res.json()

    return [
        img["urls"]["regular"]
        for img in data.get("results", [])
    ]


agent = create_react_agent(
    model=llm,
    tools=[weather_tool, web_tool, budget_tool, transport_tool, image_tool],
    prompt="""
You are an expert AI Travel Planner.
When providing transport schedules, you must display the data explicitly.
- For Flights: Extract the operator/airline name, flight schedules, departure times, and arrival times from the transport_tool.
- For Trains: Extract the specific train name, train number, and departure/arrival times.

CRITICAL REQUIREMENT: At the beginning of the itinerary, construct a clear Markdown Table containing the columns:
| Transport Name/Airline | Flight/Train Number | Departure Time | Arrival Time |

If the live data from transport_tool is blank or limited, use web_tool immediately to search for real flight/train schedules for that route (e.g., search 'Direct flights from Delhi to Mumbai timings') and build the timetable from those search results instead of skipping it.
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

        result = agent.invoke(
            {"messages": [HumanMessage(content=query)]}
        )

        interests_string = " ".join(req.intrest) if req.intrest else "tourism"
        combined_query = f"{req.To} {interests_string}"
        
        fetched_images = image_tool.invoke(combined_query)
        images = {"Gallery": fetched_images} if fetched_images else {}

        return {
            "response": result["messages"][-1].content,
            "images": images
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))