from geopy import distance
from Utils.stops import stops, intercept
from Utils.linestring_selector import LinestringSelector
from Utils.routes_analyzer import routes_analyzer
from Utils.metrics_evaluator import metrics_evaluator
from Utils.NetworkManager import send_data
import geopandas as gpd



# Step 0 Parse the GeoJSON.
#       Input: Flask request.args.get()
#       Output: user_route -> List of Point (Shapely class)

# Step 1 Find the first(I) and the last(F) user coordinates.
#       Input: user_route: a list of Point()
#       Output: 2 Point -> I and F

# Step 2 Find bus stops near I. Do the same for E.
#       Input: I and F
#       Output: 2 list Tuples: Ilist, Flist -> tuple: (bus, stop)
# N.B. User haversine() to see the distance between two Point and compare the value with a threshold



# Step 3 Do the intersection in order to find the bus lines in common.
#       Input: Ilist, Flist
#       Output: Ilist, Flist -> filtered with only the tuples (bus, stop) with bus field in I and E


# Step 4 Create a list of bus routes that have a starting point in Ilist and an end in Flist
#       Input: Ilist, Flist
#       Output: bus_routes -> list of list of Point -> every list of Point represents a bus route


# Step 5 For every route in bus_route compute its metrics.
#
#       metrics: 1) user_coordinates_matched: number of Point in user_route contained in at least
#                                             one polygon of the bus route.
#                2) polygons_matched: number of polygons of the bus route containing at least one
#                                     Point of user_route.
#
#       Input: bus_routes, user_route
#       Output: list of route_dictionary
#                           result_dict = {
#                                               'route' : bus_route,
#                                               'percentage_user': user_metric,
#                                               'number_user_coordinates': len(user_coordinates_matched),
#                                               'percentage_poly': poly_metric,
#                                               'number_polygons': len(polygons_matched)
#                                           }



# Step 6 Search the dictionary with the maximum metrics
#       Input: list of route_dictionary
#       Output: route_dictionary


# Step 7 Calculate the distance with haversine()
#       Input: route_dictionary
#       Output: km_travelled

# Step 8 Save the data in the database
#       Input: user_id, ticket_id, km_travelled

def get_bus_routes(initial_point, finishing_point):
    # STEP 2
    # Find bus stops near I. Do the same for F
    stops_object = stops(type_of_dataset='BUS')
    offset_square = 0.001
    Ilist = stops_object.find_stops_close_to(initial_point, radius=offset_square)
    Flist = stops_object.find_stops_close_to(finishing_point, radius=offset_square)
    # STEP 3
    # Do the intersection in order to find the bus lines in common
    Ilist, Flist = intercept(Ilist, Flist)
    print(f'bus stops found: {str(len(Ilist))}')
    # STEP 4
    # Create a list of bus routes that have a starting point in Ilist and an end in Flist
    linestring_selector = LinestringSelector(Ilist, Flist)
    sliced_routes = linestring_selector.get_sliced_routes()
    print(f'bus routes found: {str(len(sliced_routes))}')
    return sliced_routes

def get_train_routes(initial_point, finishing_point):
    # STEP 2
    # Find train stops near I. Do the same for F
    stops_object = stops(type_of_dataset='TRAIN')
    offset_square = 0.001
    Ilist = stops_object.find_stops_close_to(initial_point, radius=offset_square)
    Flist = stops_object.find_stops_close_to(finishing_point, radius=offset_square)
    # STEP 3
    # Do the intersection in order to find the bus lines in common
    Ilist, Flist = intercept(Ilist, Flist)
    print(f'train stops found: {Ilist}')
    # STEP 4
    # Create a list of train routes that have a starting point in Ilist and an end in Flist
    linestring_selector = LinestringSelector(Ilist, Flist, type_of_dataset="TRAIN")
    sliced_routes = linestring_selector.get_sliced_routes()
    print(f'train routes found: {str(len(sliced_routes))}')
    return sliced_routes

def detect_vehicle_and_km(raw_user_route: list, snapped_user_route: list):

    route_dictionaries = []

    try:
        # STEP 1 for buses
        # Retrieving initial and finhsing Point of user's trip
        bus_initial_point, bus_finishing_point = find_points(snapped_user_route)

        # STEP 2-4 for buses
        sliced_routes_bus = get_bus_routes(bus_initial_point, bus_finishing_point)
        sliced_routes_bus = [(x, 'BUS') for x in sliced_routes_bus]
        # STEP 5
        # For every route in sliced_routes compute its metrics.
        bus_analyzer = routes_analyzer(sliced_routes_bus, snapped_user_route)
        route_dictionaries += bus_analyzer.compute_metrics()
    except Exception as message:
        print(f"No bus route matches the user one: " + str(message))
    
    print(f"Searched for bus routes {str(len(route_dictionaries))}")

    try:
        # STEP 1 for trains
        # Retrieving initial and finhsing Point of user's trip
        train_initial_point, train_finishing_point = find_points(raw_user_route)

        # STEP 2-4 for trains
        sliced_routes_train = get_train_routes(train_initial_point, train_finishing_point)
        sliced_routes_train = [(x, 'TRAIN') for x in sliced_routes_train]
        # STEP 5
        # For every route in sliced_routes compute its metrics.
        train_analyzer = routes_analyzer(sliced_routes_train, raw_user_route)
        route_dictionaries += train_analyzer.compute_metrics()
    except Exception as message:
        print(f"No train route matches the user one: " + str(message))

    print(f"Searched for train routes {str(len(route_dictionaries))}")


    if len(route_dictionaries) != 0:
        #print("Space race between:")
        #for route in route_dictionaries:
        #    print(route['route'][0])
        #    print(route['route'][len(route['route']) - 1])
        #    print(route['percentage_user'])
        #    print(route['number_user_coordinates'])
        #    print(route['percentage_poly'])
        #    print(route['number_polygons'])
        #    print('-------------------------------------')
        
        # STEP 6
        # Search the dictionary with the maximum metrics
        evaluator = metrics_evaluator(route_dictionaries)
        best_route = evaluator.evaluate()

        print("winner")
        print(best_route['route'][0])
        print(best_route['route'][len(best_route['route']) - 1])
        print(best_route['percentage_user'])
        print(best_route['number_user_coordinates'])
        print(best_route['percentage_poly'])
        print(best_route['number_polygons'])

        # STEP 7
        # Calculate the distance with haversine
        print(best_route['route'][0])
        print(best_route['route'][len(best_route['route']) - 1])
        print('route len ' + str(len(best_route['route'])))

        km_travelled = compute_kilometers(best_route['route'])
        vehicle = best_route['vehicle']
        return vehicle, km_travelled

    else:
        # No match is found
        return None, 0


#   Find the first & last user coordinates.
#   params:  - user_route: a list of Point()
#   returns: - the first point of the user route
def find_points(user_route):
    return user_route[0], user_route[len(user_route) - 1]


#Given a route (list of Point) returns the kilometers of that route
def compute_kilometers(route: list):
    total_km = 0
    route_length = len(route)
   

    for point in range(route_length - 1):
        p1 = route[point]
        p2 = route[point + 1]
        p1 = (p1.x,p1.y)
        p2 = (p2.x, p2.y)
    
        total_km += distance.geodesic(p1, p2, ellipsoid='Intl 1924').km

    return total_km


def elaborate_request(user_id, ticket_id, start_time, end_time, raw_data, snapped_data):
    # STEP 0
    # Create the JSON to save in the Database.
    user_data = {
        'user_id' : user_id,
        'ticket_id' : ticket_id,
        'km_travelled' : None,
        'transportation' : None,
        'start_time' : start_time,
        'end_time' : end_time
        }

    # STEP 1-7
        
    
    vehicle, km_travelled = detect_vehicle_and_km(raw_user_route=raw_data, snapped_user_route=snapped_data)
    user_data['km_travelled'] = km_travelled
    user_data['transportation'] = vehicle

    return user_data