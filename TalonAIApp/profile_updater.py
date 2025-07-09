import re
from typing import Dict, Any, Optional
from asgiref.sync import sync_to_async
from .models import CarProfile

def extract_car_info_from_query(query: str) -> Dict[str, Any]:
    """
    Extract car information from user query using pattern matching
    """
    car_info = {}
    
    # Extract name
    name_patterns = [
        r"my name is (\w+)",
        r"i'm (\w+)",
        r"i am (\w+)",
        r"call me (\w+)"
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, query.lower())
        if match:
            car_info["name"] = match.group(1).title()
            break
    
    # Extract car make and model
    car_patterns = [
        r"(\d{4})\s+(\w+)\s+(\w+(?:\s+\w+)*)",  # 2020 Honda Civic Si
        r"(\w+)\s+(\w+(?:\s+\w+)*)\s+(\d{4})",  # Honda Civic Si 2020
        r"i drive a (\d{4})\s+(\w+)\s+(\w+(?:\s+\w+)*)",  # I drive a 2020 Honda Civic
        r"i have a (\d{4})\s+(\w+)\s+(\w+(?:\s+\w+)*)",  # I have a 2020 Honda Civic
    ]
    
    for pattern in car_patterns:
        match = re.search(pattern, query.lower())
        if match:
            groups = match.groups()
            if len(groups) >= 3:
                # Try to determine which group is year, make, model
                year_candidates = [g for g in groups if g.isdigit() and len(g) == 4]
                if year_candidates:
                    year = year_candidates[0]
                    remaining = [g for g in groups if g != year]
                    if len(remaining) >= 2:
                        car_info["year"] = int(year)
                        car_info["make"] = remaining[0].title()
                        car_info["model"] = remaining[1].title()
            break
    
    # Extract performance interests
    performance_keywords = [
        "performance", "track", "racing", "modifications", "mods", 
        "horsepower", "turbo", "supercharger", "tune", "exhaust"
    ]
    
    if any(keyword in query.lower() for keyword in performance_keywords):
        car_info["performance_interest"] = True
    
    return car_info

@sync_to_async
def update_car_profile_from_query(user_id: str, query: str) -> bool:
    """
    Update car profile based on extracted information from query
    """
    try:
        car_info = extract_car_info_from_query(query)
        
        if not car_info:
            return False
        
        profile, created = CarProfile.objects.get_or_create(
            user_id=user_id,
            defaults={
                "make": "",
                "model": "",
                "year": 2020,
                "resale_pref": ""
            }
        )
        
        updated = False
        
        if "make" in car_info and car_info["make"] and not profile.make:
            profile.make = car_info["make"]
            updated = True
        
        if "model" in car_info and car_info["model"] and not profile.model:
            profile.model = car_info["model"]
            updated = True
        
        if "year" in car_info and car_info["year"] and profile.year == 2020:
            profile.year = car_info["year"]
            updated = True
        
        if "performance_interest" in car_info and not profile.resale_pref:
            profile.resale_pref = "performance"
            updated = True
        
        if updated:
            profile.save()
            return True
        
        return False
        
    except Exception as e:
        print(f"⚠️ Error updating car profile: {e}")
        return False

def format_car_profile_summary(car_profile: Dict[str, Any]) -> str:
    """
    Format car profile into a readable summary
    """
    if not car_profile:
        return "No car profile information available."
    
    make = car_profile.get("make", "")
    model = car_profile.get("model", "")
    year = car_profile.get("year", "")
    
    if make and model:
        car_str = f"{year} {make} {model}" if year and year != 2020 else f"{make} {model}"
    elif make:
        car_str = f"{year} {make}" if year and year != 2020 else make
    else:
        car_str = "Unknown vehicle"
    
    summary = f"Vehicle: {car_str}"
    
    if car_profile.get("resale_pref"):
        summary += f"\nPreferences: {car_profile['resale_pref']}"
    
    if car_profile.get("mods"):
        summary += f"\nCurrent mods: {len(car_profile['mods'])} installed"
    
    if car_profile.get("symptoms"):
        summary += f"\nActive issues: {len(car_profile['symptoms'])} reported"
    
    return summary 