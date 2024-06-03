#!/usr/bin/python

# Implementation of the game Mafia (Cidade Dorme) in Python

import random
import re

from ollama import Client
import argparse

RANDOM_AGENT = False


def ask_llm(message):
    client = Client(host=args.host)
    response = client.chat(model=args.model, messages=[
    {
        'role': 'user',
        'content': message+"\n"+"Limit your message to 50 words",
        # 'raw' : True,
        # 'model': "llama-3-70B"
    },
    ])

    return response["message"]["content"]

def get_llm_template_message(player, role, knowledge):
    knowledge_as_str = "\n".join(knowledge)
    return f''' You are an AI agent that will play the game Mafia (Cidade Dorme) as a {role}.
    You are the player {player}.
    If you is a Mafia, you should lie and hide your real intentation and try to convince other players to not vote in you.
    If you are an Investigator, you can share what you discovered in your previous investigation.
    If you are an Citizen, you should try to find the Mafia players.
    Dont answer dramatically, just answer what you think is the best for you.
    Your knowledge (what you know that happened so far is) is: {knowledge_as_str}
    '''

# Function to shuffle the roles
def shuffle_roles(roles):
    random.shuffle(roles)
    return roles

# Function to distribute the roles
def distribute_roles(players, roles):
    roles = shuffle_roles(roles)
    
    roles_dict = {}
    for i in range(0, len(players)):
        print(players[i] + " is a " + roles[i])
        roles_dict[players[i]] = roles[i]
    
    return roles_dict

# Function to start the game
def start_game():
    players = ["Player 1", "Player 2", "Player 3", "Player 4", "Player 5", "Player 6"]
    roles = ["Mafia", "Mafia", "Investigator", "Citizen", "Citizen", "Citizen"]


    players = ["Player 1", "Player 2", "Player 3", "Player 4", "Player 5", "Player 6"] + [f"Player {x}" for x in range(7, 7+4)]
    roles = ["Mafia", "Mafia", "Investigator", "Citizen", "Citizen", "Citizen"] + ["Citizen"]*4

    return distribute_roles(players, roles)


def create_state(roles_dict):
    state = {
        "players": list(roles_dict.keys()),
        "roles": list(roles_dict.values()),
        "roles_dict": roles_dict,
        "players_knowledge": {
            x: [] for x in roles_dict.keys()
        },
        "votes": {
            x: None for x in roles_dict.keys()
        },
        "votes_count": {
            "Player 1": 0,
            "Player 2": 0,
            "Player 3": 0,
            "Player 4": 0,
            "Player 5": 0,
            "Player 6": 0
        },
        "votes_done": 0,
        "night": False,
        "day": False,
        "mafia": [],
        "citizens": [],
        "investigator": [],
        "alive_players": list(roles_dict.keys()),
        "last_murdered": [],
    }

    for player, role in roles_dict.items():
        if role == "Mafia":
            state["mafia"].append(player)
        elif role == "Citizen":
            state["citizens"].append(player)
        else:
            state["investigator"].append(player)

    for player, role in roles_dict.items():
        if role == "Mafia":
            partners = "\n".join([x for x in state["mafia"] if x != player])
            state["players_knowledge"][player].append(f"I am a Mafia! My partners are: \n{partners}")
        elif role == "Citizen":
            state["players_knowledge"][player].append("I am a Citizen!")
        else:
            state["players_knowledge"][player].append("I am a Investigator!")

    return state

def add_global_knowledge(state, message, role=None):
    for player in state["players"]:
        if role is None or state["roles_dict"][player] == role:
            state["players_knowledge"][player].append(message)

def run_day(state):
    state["day"] = True
    state["night"] = False

    print("\nDay has started!")
    add_global_knowledge(state, "Day has started!")
    print("Players alive: " + str(state["alive_players"]))
    add_global_knowledge(state, "Players alive:\n" + "\n".join(state["alive_players"]))
    
    comments = []
    for player in state["alive_players"]:

        if RANDOM_AGENT:
            player_comment = "My last knowledge is: " + state["players_knowledge"][player][-1]
            player_comment = "Player " + player + " says: " + player_comment
        else:
            llm_context = get_llm_template_message(player, state["roles_dict"][player], state["players_knowledge"][player])
            llm_question = "You now should comment about what happened and maybe point who should be voted to be killed. If you are Mafia, you should lie and hide your real intentation and try to convince other players to not vote in you. If you are an Investigator, you can share what you discovered in your previous investigation. All other players will see your comment."
            # print(llm_context + llm_question)
            player_comment = f"{player} comment: " + ask_llm(llm_context + llm_question)

        print(player_comment)
        comments.append(player_comment)

    for comment in comments:
        add_global_knowledge(state, comment)

    # Reset votes
    state["votes"] = {x: None for x in state["roles_dict"].keys()}
    state["votes_count"] = {x: 0 for x in state["roles_dict"].keys()}
    state["votes_done"] = 0

    for player in state["alive_players"]:

        if RANDOM_AGENT:
            vote = random.choice(state["alive_players"])
        else:
            llm_context = get_llm_template_message(player, state["roles_dict"][player], state["players_knowledge"][player])
            llm_question = "Who do you want to vote to be killed? You shouldn't vote on your self. All other players will be able to see your vote. Answer only one of the target possibilities and nothing more. Your possible targets are:\n" + str("\n".join(state["alive_players"]))
            # print(llm_context + llm_question)
            llm_resp = ask_llm(llm_context + llm_question)
            vote = llm_resp

            # Extract the vote from the response using regex
            # Get the last number in the response
            vote = re.findall(r'\d+', llm_resp)[-1]
            vote = "Player " + vote

            print("[Voting argument] LLM response: " + llm_resp)
            
            if vote not in state["alive_players"]:
                print("Invalid vote, choosing random target: ", end="")
                vote = random.choice(state["alive_players"])
                print(vote)
            
        state["votes"][player] = vote
        state["votes_count"][vote] += 1
        state["votes_done"] += 1
        add_global_knowledge(state, f"{player} voted to kill {vote}")
        print(f"{player} voted to kill {vote}")

    most_voted = max(state["votes_count"], key=state["votes_count"].get)
    # Kill the most voted
    state["last_murdered"] = [most_voted]
    state["alive_players"].remove(most_voted)

    most_voted_msg = f"{most_voted} was killed by the citizens!"
    print(most_voted_msg)
    add_global_knowledge(state, most_voted_msg)

    if state["roles_dict"][most_voted] == "Mafia":
        add_global_knowledge(state, f"{most_voted} was a Mafia!")

def check_game_over(state):
    # Check if the game is over

    mafia_not_dead = [x for x in state["mafia"] if x in state["alive_players"]]
    citizens_not_dead = [x for x in state["citizens"] if x in state["alive_players"] ]
    citizens_not_dead += [x for x in state["investigator"] if x in state["alive_players"] ]

    if len(mafia_not_dead) >= len(citizens_not_dead):
        print("Game over! Mafia wins!")
        add_global_knowledge(state, "Game over! Mafia wins!")
        exit()
    elif len(mafia_not_dead) == 0:
        print("Game over! Citizens win!")
        add_global_knowledge(state, "Game over! Citizens win!")
        exit()
    else:
        print("Game continues...")
        add_global_knowledge(state, "Game continues...")

def run_night(state):
    state["day"] = False
    state["night"] = True

    print("\nNight has started!")
    add_global_knowledge(state, "Night has started!")
    
    mafia_votes = {x: 0 for x in state["alive_players"]}
    for mafia in state["mafia"]:
        if mafia not in state["alive_players"]:
            continue

        players_not_mafia = [x for x in state["alive_players"] if x not in state["mafia"]]

        players_not_mafia_alives = [x for x in players_not_mafia if x in state["alive_players"]]
        
        if RANDOM_AGENT:
            vote = random.choice(players_not_mafia_alives)
        else:
            
            llm_context = get_llm_template_message(mafia, state["roles_dict"][mafia], state["players_knowledge"][mafia])
            llm_question = "Who do you want to kill? Answer only one of the target possibilities and nothing more. Your possible targets are:\n" + str("\n".join(players_not_mafia_alives))
            # print(llm_context + llm_question)
            llm_resp = ask_llm(llm_context + llm_question)
            vote = llm_resp

            # Extract the vote from the response using regex
            # Get the last number in the response
            vote = re.findall(r'\d+', llm_resp)[-1]
            vote = "Player " + vote

            print("[Mafia] LLM response: " + llm_resp)
            
            if vote not in players_not_mafia_alives:
                print("Invalid vote, choosing random target: ", end="")
                vote = random.choice(players_not_mafia_alives)
                print(vote)


        mafia_votes[vote] += 1
        
        add_global_knowledge(state, f"Mafia {mafia} vote to kill {vote}", "Mafia")
    
    print("Mafia votes: " + str(mafia_votes))

    for inv in state["investigator"]:
        if inv not in state["alive_players"]:
            continue

        # Remove the investigator from the possible targets
        players_not_inv = [x for x in state["alive_players"] if x != inv]
        if RANDOM_AGENT:
            investigated = random.choice(players_not_inv)
        else:
            llm_context = get_llm_template_message(inv, state["roles_dict"][inv], state["players_knowledge"][inv])
            llm_question = "You can choose to investigate a player and find out if it is a Mafia or a Citizen player. You cannot investigate your self. Who do you want to investigate? Answer only one of the target possibilities and nothing more. Your possible targets are:\n" + str("\n".join(players_not_inv))
            # print(llm_context + llm_question)
            llm_resp = ask_llm(llm_context + llm_question)
            investigated = llm_resp

            # Extract the vote from the response using regex
            # Get the last number in the response
            investigated = re.findall(r'\d+', llm_resp)[-1]
            investigated = "Player " + investigated

            print("[Investigator] LLM response: " + llm_resp)

        
        state["players_knowledge"][inv].append(f"Investigating {investigated} and found out that he is a {state['roles_dict'][investigated]}")
    
        print(f"Investigator {inv} investigated {investigated} and found out that he is a {state['roles_dict'][investigated]}")
    
    mafia_target = max(mafia_votes, key=mafia_votes.get)
    state["last_murdered"] = [mafia_target]
    state["alive_players"].remove(mafia_target)

    mafia_target_msg = f"{mafia_target} was killed by the Mafia!"
    print(mafia_target_msg)
    add_global_knowledge(state, mafia_target_msg)


# Main function
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Query the Ollama API')
    parser.add_argument('--host', type=str, default='http://localhost:11434', help='The host of the Ollama API')
    parser.add_argument('--model', type=str, default='llama3', help='The model to use')
    parser.add_argument('--message', type=str, default='Why is the sky blue?', help='The message to send')
    args = parser.parse_args()

    roles_dict = start_game()
    state = create_state(roles_dict)
    # print(roles_dict)
    # print(state)

    for i in range(10):
        check_game_over(state)
        run_night(state)
        check_game_over(state)
        run_day(state)