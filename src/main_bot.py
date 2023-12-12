"""
Main Bot module.

This module uses the Telegram API to serve as a GPS Telegram Bot that will
guide you to wherever you want. Use the /help command to know more on the
available commands.
"""

import os
from datetime import datetime
from typing import NewType, Optional, Any, Tuple, Dict

from geopy.geocoders import Photon
from haversine import haversine
from telegram import Update
from telegram.ext import ContextTypes, Application, \
    CommandHandler, MessageHandler, filters

from src.guide import Guide


# Custom data type to make the code easier to read:
Coordinates = NewType(name='Coordinates', tp=Tuple[float, float])  # (lat, lon)


# GLOBAL OBJECTS:
# Guide instance to compute the shortest paths and route instructions
GUIDE = Guide()
# Geocoder using Photon geocoding service (data based on OpenStreetMap and
# service provided by Komoot on https://photon.komoot.io).
GEOLOCATOR = Photon()


def _is_moving_away_from_the_route(
        current_coords: Coordinates,
        last_coords: Coordinates,
        checkpoint: Coordinates,
        margin: int = 15,
) -> bool:
    """
    Checks whether the user is moving away from the next checkpoint. If the
    user is following the route, their current position (<current_coords>) must
    be closer to the next checkpoint than the last recorder position (<last_
    coords>). We give a certain <margin> (in meters) for some tolerance.

    :param current_coords: (x,y) coordinates. The current coords of the user
    :param last_coords: (x,y) coordinates. The last recorded coords of the user
    :param checkpoint: (x,y) coordinates of the next checkpoint in the route
    :param margin: distance difference to consider that the user is moving away
    :return: True if the user is moving away from the next checkpoint
    """

    last_distance = haversine(last_coords, checkpoint, unit='m')
    current_distance = haversine(current_coords, checkpoint, unit='m')
    return current_distance > last_distance + margin


def _are_next_to_each_other(
        p1: Coordinates,
        p2: Coordinates,
        margin: int = 15
) -> bool:
    """
    Checks whether the distance between two geographic coordinates (p1 and p2)
    is lower than a given threshold (<margin>) [in meters]. If that is the
    case, the points are considered to be "next to each other".

    :param p1: (x,y) coordinates of the first point
    :param p2: (x,y) coordinates of the second point
    :param margin: distance threshold to define closeness [in meters]
    :return: True if the two points are closer than a given distance (margin)
    """

    distance = haversine(point1=p1, point2=p2, unit='m')
    return distance <= margin


def _round5(n: float) -> int:
    """
    Returns the multiple of 5 that is closer to the given number <n>.
    E.g.  756->755;  758->760;  802->800;  803->805;

    :param n: input number
    :return: the multiple of 5 that is closer to the given number <n>
    """

    n5 = int((n // 5) * 5)
    return n5 if n % 5 <= 2 else n5 + 5


def _get_turning_message(angle: Optional[float]) -> str:
    """
    Returns the message indicating the direction of the next turning.
    The message depends on the given <angle>, which is in the range from -180
    to 180:

    - Positive angle (+): to the right
    - Negative angle (-): to the left
    - Very small angle (<22.5º) or None: Go straight ahead
    - Small angle (<67.5º): Half-turn
    - Moderate angle (<112.5): basic turn
    - Large angle (>112.5º): sharp turn

    :param angle: [Optional] angle in degrees [float]
    :return: the message
    """

    if abs(angle) < 22.5 or angle is None:
        message_ = 'Go straight ahead ⬆️'
    else:
        dir_ = 'left' if angle < 0 else 'right'  # direction
        if abs(angle) < 67.5:
            sym_ = '↗️' if dir_ == 'right' else '↖️'
            message_ = f'Half-turn to the {dir_} {sym_}'
        elif abs(angle) < 112.5:
            sym_ = '➡️' if dir_ == 'right' else '⬅️'
            message_ = f'Turn to the {dir_} {sym_}'
        else:  # > 112.5 (but <= 180 by definition)
            sym_ = '↘️' if dir_ == 'right' else '↙️'
            message_ = f'Sharp turn to the {dir_} {sym_}'
    return message_


def _get_next_checkpoint_message(user_data: Dict[str, Any]) -> str:
    """
    Based on the user data and their current state of the route, return the
    message that tells the user how to arrive at the next checkpoint.

    NOTE: this message must be sent when the user reaches the n-th checkpoint
    and want to reach the (n+1)-th checkpoint.

    :param user_data: Dictionary with the user data (directions, current step)
    :return: message informing the user on how to reach the next checkpoint
    """

    # Unpack user data
    current_leg = user_data['current_leg']  # already updated for next step
    current_route_leg = user_data['directions'][current_leg]
    src, mid = current_route_leg['src'], current_route_leg['mid']

    # Create the first part of the message
    message = (
        f"Well done! You've reached checkpoint #{current_leg}! 👏\n"
        f"You are at {src} 📍\n\n"
        f"Go to the next checkpoint #{current_leg+1}:\n"
        f"Coordinates: {mid} 📍\n"
    )
    # If the next street name is available, add it
    if current_route_leg['next_name'] is not None:
        message += f'Street Name: {current_route_leg["next_name"]}\n'
    message += '\n'
    # If the next distance to walk or drive is not available, compute it
    distance = current_route_leg['length']
    if distance is None:
        distance = haversine(src, mid, unit='m')
    distance = _round5(n=distance)

    if current_route_leg['dst'] is None:
        # The next checkpoint is the destination!
        message += (
            "Your destination is close to you!\n"
            f"Only {distance} meters left 💪!"
        )
    else:  # Give instructions on how to reach the next checkpoint
        # Try to get the current street name
        current_street = current_route_leg['current_name']
        if current_street is None:
            current_street = "the street"
        # Tell the user how many meters he/she has to walk/drive
        message += f"Go straight through {current_street} {distance} meters"
        if (current_route_leg['angle'] is not None
                and abs(current_route_leg['angle']) > 22.5):
            turning_m = _get_turning_message(current_route_leg['angle'])
            message += f' and {turning_m.lower()}'

    return message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Starts the conversation. Command: /start.

    :param update: object that represents an incoming update
    :param context: provides access to common objects in handler callbacks
    :return: None. A message is sent to the user.
    """

    # Reset the user data, just in case
    for v in ('directions', 'dst_name', 'current_leg', 'route_id'):
        if v in context.user_data:
            del context.user_data[v]
    message = (
        f"Hello {update.effective_chat.first_name}! 👋\n\n"
        "Don't get lost anymore 🌍,\nGuideMateBot will help you! 🧭\n\n"
        "Please, use the /help command to get more information 🙌\n\n"
        "If you already know how to use this Bot, share your location📍 and"
        " use the /go command 😎!"
    )
    user_id = update.effective_user.id  # get the user_id to send messages
    await context.bot.send_message(chat_id=user_id, text=message)


async def help_(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Provides the user with instructions on how to use the Bot, and a brief
    explanation about the available commands. Command /help.

    :param update: object that represents an incoming update
    :param context: provides access to common objects in handler callbacks
    :return: None. A message is sent to the user.
    """

    message = (
        "Dont' know how to use this bot? Don't worry! "
        "I'm here to give you a hand 😉!\n\n"
        "/start -> sends a welcome message 👋\n"
        "/help -> gives you the basic instructions 🙌\n"
        "/where -> tells you where you are now 🏙️\n"
        "/cancel -> cancels the programmed route ❎\n"
        "/go <destination> -> This Bot will guide you from your current "
        "position to your _destination_📍\n\n\n"
        "❗ IMPORTANT NOTE ❗:\n\n"
        "For this Bot to work well, you must share your location 🛰️. "
        "Make sure to do this before calling the /go command 👍"

    )
    user_id = update.effective_user.id  # get the user_id to send messages
    await context.bot.send_message(chat_id=user_id, text=message)


async def where(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Tells the users where they are right now(city, street, coordinates, etc.)
    Command: /where.

    NOTE: to provide this information, users must share their location.
    If that is not the case, another different message will be sent.

    :param update: object that represents an incoming update
    :param context: provides access to common objects in handler callbacks
    :return: None. A message is sent to the user.
    """

    user_id = update.effective_user.id  # get the user_id to send messages
    try:
        # try to get the user location (if he/she is sharing his/her location)
        user_coords = context.user_data['current_location']
        info = GEOLOCATOR.reverse(user_coords).raw['properties']
        message = (
            f"You are here📍:\n\nCountry: {info.get('country')}\n"
            f"City: {info.get('city')}, ({info.get('postcode')})\n"
            f"Type: {info.get('osm_value')}, {info.get('type')}\n"
            f"Street Name: {info.get('name')}\n"
            f"Coordinates: {user_coords}"
        )
        await context.bot.send_message(chat_id=user_id, text=message)
    except:
        # It may be that 'current_location' is not in <context.user_data>
        message = (
            "I don't know where you are...\n"
            "Please, share your location with me📍"
        )
        await context.bot.send_message(chat_id=user_id, text=message)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Cancels the current route. No more instructions will be sent.
    Command: /cancel

    NOTE: to provide this information, users must have a programmed route.
    If that is not the case, another different message will be sent.

    NOTE: the location of the user it is not removed. If the user is still
    sharing their location, the bot will keep updating the current location
    of the user, just in case it calls the /go command again

    :param update: object that represents an incoming update
    :param context: provides access to common objects in handler callbacks
    :return: None. A message is sent to the user.
    """

    user_id = update.effective_user.id  # get the user_id to send messages
    try:  # If there is an ongoing route, remove it from the user data
        del context.user_data['directions']
        del context.user_data['dst_name']
        del context.user_data['current_leg']
        del context.user_data['route_id']
        message = (
            "Your rute has been canceled ❎\n"
            "Use the /go command to create a new one 🗺️\n"
        )
        await context.bot.send_message(chat_id=user_id, text=message)
    except:
        # There are no programmed routes for this user.
        message = (
            "You don't have any programmed route 💭\n\n"
            "Use the /go command to create a new one 🗺️\n"
            "Make sure you are sharing your location!"
        )
        await context.bot.send_message(chat_id=user_id, text=message)


async def go(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Leverages the GUIDE global object to compute the shortest path from the
    current location of the user to the destination (input args). From now on,
    the Bot will track the user's location and send messages to guide him/her
    to his/her destination. Command: /go.

    :param update: object that represents an incoming update
    :param context: provides access to common objects in handler callbacks
    :return: None. A new route is programmed and a message is sent to the user.
    """

    user_id = update.effective_user.id  # get the user_id to send message
    try:
        if not context.args:  # If the destination is not provided
            raise Exception("EmptyInputDestinationError")
        if 'directions' in context.user_data:  # If he/she already has a route
            raise Exception('AlreadyHasRouteError')
        if 'current_location' not in context.user_data:
            raise Exception('NoLocationFoundError')

        # Turn the destination name into coordinates and compute the route
        current_coords = context.user_data['current_location']
        destination_name = ' '.join(context.args)
        context.user_data['dst_name'] = destination_name
        dst_place = destination_name + ', ' + GUIDE.city
        dst_geoinfo = GEOLOCATOR.geocode(query=dst_place)
        dst_coords = (dst_geoinfo.latitude, dst_geoinfo.longitude)

        # Compute the route: shortest path to the given destination
        directions = GUIDE.get_directions(
            src_coords=current_coords, dst_coords=dst_coords
        )

        context.user_data['directions'] = directions  # save the route
        # Create a route_id from the current timestamp
        context.user_data['route_id'] = datetime.now().strftime("%H%M%S")

        # Send image showing the route to follow
        img_filepath = GUIDE.plot_directions(
            directions=directions,
            current_leg=0,
            file_name=f'{context.user_data["route_id"]}_0.png'
        )
        await context.bot.send_photo(chat_id=user_id, photo=img_filepath)

        # Send the first text message
        first_leg = context.user_data['directions'][0]
        first_src, first_mid = first_leg['src'], first_leg['mid']

        # The user must go to the first checkpoint
        context.user_data['current_leg'] = 0
        message = (
            f'You are at {first_src}\n\n'
            f'Go to the first Checkpoint #1:\n {first_mid}\n'
        )
        if first_leg['next_name'] is not None:
            message += f'Street name: {first_leg["next_name"]}'
        await context.bot.send_message(chat_id=user_id, text=message)

    except Exception as e:
        print(e)
        if str(e) == 'EmptyInputDestinationError':
            message = "Please, insert your destination after /go"
            await context.bot.send_message(chat_id=user_id, text=message)
        elif str(e) == "AlreadyHasRouteError":
            message = (
                "You are already following a route! 😅\n\nIf you want to "
                "delete it and start a new one, use the /cancel command."
            )
            await context.bot.send_message(chat_id=user_id, text=message)
        elif str(e) == 'NoLocationFoundError':
            message = (
                "I don't know where you are 😅\n\nPlease, share your "
                "location with me, so I can guide you wherever you want! 🌎"
            )
            await context.bot.send_message(chat_id=user_id, text=message)
        else:
            message = (
                'Your destination is not reachable.\n'
                'Please, try another one.'
            )
            await context.bot.send_message(chat_id=user_id, text=message)


async def process_user_location(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    When the user is sharing their location, this function process that
    position. If there is a programmed route, it checks that everything is
    okay. It sends a message to the user if it is needed.

    NOTE: this function is called only while users are sharing their location,
    and they are moving (constantly changing their position)

    :param update: object that represents an incoming update
    :param context: provides access to common objects in handler callbacks
    :return: None. The location of the user (if shared) is processed
    """

    user_id = update.effective_user.id
    try:
        # Try to get the current location (latitude, longitude) of the user.
        if update.edited_message:
            message = update.edited_message
        else:
            message = update.message
        current_loc = (message.location.latitude, message.location.longitude)

        if 'current_location' not in context.user_data:
            # This is the first location received from the user.
            context.user_data['current_location'] = current_loc
            loc_geoinfo = GEOLOCATOR.reverse(current_loc).raw['properties']
            place = loc_geoinfo['city'] + ', ' + loc_geoinfo['country']
            GUIDE.get_graph(place=place, walk_or_drive='drive')
            message = (
                'Great! 👍\nNow that I have your location, '
                'I can take you wherever you want! 🌍'
                'Just use the /go command 😉'
            )
            await context.bot.send_message(chat_id=user_id, text=message)
            return  # there is no route yet, nothing left to do

        # Save the current location of the user in the 'user_data' dictionary
        # in the 'context' object. Keep the last_location at hand.
        last_location = context.user_data['current_location']
        context.user_data['current_location'] = current_loc

        # When a user has a programmed route,
        # they have a 'directions' key in their data.
        user_data = context.user_data
        if 'directions' in user_data:
            # There is a programmed route. Let's check that the user is
            # approaching the next checkpoint, and the instructions will be
            # updated depending on the user's progress.
            directions, i = user_data['directions'], user_data['current_leg']
            checkpoint = directions[i]['mid']  # the next checkpoint

            # First, let's check that the user is not moving away from the
            # programmed route. In other words, let's check that the user is
            # getting closer to the next checkpoint.
            is_moving_away = _is_moving_away_from_the_route(
                current_coords=context.user_data['current_location'],
                last_coords=last_location,
                checkpoint=checkpoint
            )
            if is_moving_away:
                # The user is moving away from the next checkpoint.
                # A warning message is required to let him/her know that.
                warning = (
                    "⚠️ Be careful ⚠️\n\n"
                    "You may be moving away from the next checkpoint ❗️"
                )
                await context.bot.send_message(chat_id=user_id, text=warning)

            elif _are_next_to_each_other(p1=current_loc, p2=checkpoint):
                # The user has reached the checkpoint. Send a message informing
                # about this milestone. If the checkpoint is the destination,
                # send the final message (congratulation). Else, send further
                # instructions to reach the next checkpoint.

                if i+1 == len(directions):
                    img_filepath = GUIDE.plot_directions(
                        directions=user_data['directions'],
                        current_leg=i+1,
                        file_name=f'{user_data["route_id"]}_{i+1}.png'
                    )
                    await context.bot.send_photo(
                        chat_id=user_id, photo=img_filepath
                    )

                    # We've already reached our destination! send final message
                    user_name = update.effective_chat.first_name
                    destination_name = context.user_data['dst_name']

                    final_m = (
                        f'Congratulations {user_name} 👏 !!!\n'
                        f'You are at {destination_name} 📍\n\n'
                        f'Our trip is over, no more checkpoints left 😉\n'
                        'Thanks for trusting me 🤝,\n'
                        'See you soon 😉!'
                    )
                    await context.bot.send_message(
                        chat_id=user_id, text=final_m
                    )
                    # Finally, remove everything related to this finished route
                    del context.user_data['directions']
                    del context.user_data['dst_name']
                    del context.user_data['current_leg']
                    del context.user_data['route_id']

                else:  # next checkpoint reached (it is not the destination)

                    # Send message with info to reach the next checkpoint
                    message = _get_next_checkpoint_message(
                        user_data=context.user_data
                    )
                    await context.bot.send_message(
                        chat_id=user_id, text=message
                    )

                    if directions[i]['angle'] is not None:
                        # If possible, we will remind the user of their
                        # turning direction
                        turn_ = _get_turning_message(directions[i]['angle'])
                        await context.bot.send_message(
                            chat_id=user_id, text=turn_
                        )

                    # Advance the step counter
                    context.user_data['current_leg'] += 1
                    leg_id = context.user_data['current_leg']
                    img_filepath = GUIDE.plot_directions(
                        directions=user_data['directions'],
                        current_leg=leg_id,
                        file_name=f'{user_data["route_id"]}_{leg_id}.png'
                    )
                    await context.bot.send_photo(
                        chat_id=user_id, photo=img_filepath
                    )
            # ELSE: do nothing, wait until he/she moves to a different position

    except Exception as e:
        # When: the user is sharing the location but the bot doesn't receive it
        print(e)
        message = (
            "There is a problem with your GPS signal 🛰😵\n\n"
            "I am trying to fix it...\n"
            "Please, check that everything is okay.\n"
            "You may have to share your location again."
        )
        await context.bot.send_message(chat_id=user_id, text=message)


if __name__ == '__main__':

    # 1) Read the token of your bot
    # (you can create it by speaking to the BotFather in the Telegram app)
    this_file_path = os.path.abspath(__file__)
    this_project_dir_path = '/'.join(this_file_path.split('/')[:-2])
    toke_filepath = this_project_dir_path + '/token.txt'
    with open(toke_filepath, 'r') as token_file:
        token = token_file.read().strip()

    # 2) Create the Application and pass it your bot's token.
    application = Application.builder().token(token).build()

    # 3) Enable the different commands available for this Bot
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler('help', help_))
    application.add_handler(CommandHandler('go', go))
    application.add_handler(CommandHandler('where', where))
    application.add_handler(CommandHandler('cancel', cancel))
    application.add_handler(
        MessageHandler(filters.LOCATION, process_user_location)
    )

    # 4) Run the bot until the user presses Ctrl-C
    print('running')
    application.run_polling(allowed_updates=Update.ALL_TYPES)

    print('done!')
