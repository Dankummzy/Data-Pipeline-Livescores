import json
import requests
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
import threading
import datetime

TOPIC_NAME = "livescores"
KAFKA_SERVER = 'localhost:9092'

producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
)

consumer = KafkaConsumer(
    bootstrap_servers=KAFKA_SERVER,
    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
    group_id='livescores-group'  # Assign a group ID to the consumer
)

# Assign the consumer to the topic partition explicitly
topic_partition = TopicPartition(topic=TOPIC_NAME, partition=0)
consumer.assign([topic_partition])

consumer_lock = threading.Lock()

# Replace this with your Sportmonks API token
api_token = "QDpuuJM1wzlBNDssJAxF2JVXnZraza3dA5WdVVZsMP2jrgvi6TIPE3n17Ug0"

def consume_messages():
    with consumer_lock:
        for message in consumer:
            yield 'data: {}\n\n'.format(json.dumps(message.value))


def fetch_data():
    url = "https://api.sportmonks.com/v3/football/livescores"
    headers = {
        "Authorization": f"Bearer {api_token}"
    }
    params = {
        "api_token": api_token,
        "include": "statistics;participants;scores"
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        matches = data.get("data", [])
        print(matches)
        return matches
    else:
        print('Failed to fetch data from the API:', response.content)
        return []


def send_data_to_kafka():
    matches = fetch_data()
    if isinstance(matches, list) and len(matches) > 0:
        for match in matches:
            producer.send(TOPIC_NAME, value=match)
        producer.flush()


def get_matches(request):
    url = "https://api.sportmonks.com/v3/football/livescores/latest"
    headers = {
        "Authorization": f"Bearer {api_token}"
    }
    params = {
        "api_token": api_token,
        "include": "scores"
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        matches = data.get("data", [])

        match_info_list = []
        for match in matches:
            event_id = match.get("id")
            home_team, away_team = match.get("name").split(" vs ")

            # Find the scores for home and away team
            scores = match.get("scores", [])
            home_score = "-"
            away_score = "-"
            for score in scores:
                if score.get("description") == "CURRENT":
                    if score.get("score", {}).get("participant") == "home":
                        home_score = score.get("score", {}).get("goals", "-")
                    elif score.get("score", {}).get("participant") == "away":
                        away_score = score.get("score", {}).get("goals", "-")

            match_info = {
                "event_id": event_id,
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
            }
            match_info_list.append(match_info)

        context = {'matches': match_info_list}
        print(context)
        return render(request, 'livescore/matches.html', context)
    else:
        return JsonResponse({'error': 'Failed to fetch matches.'}, status=response.status_code)


def team_analysis(request, event_id):
    if not event_id:
        return JsonResponse({'error': 'Match ID is required.'}, status=400)

    url = f"https://api.sportmonks.com/v3/football/fixtures/{event_id}"
    headers = {
        "Authorization": f"Bearer {api_token}"
    }
    params = {
        "api_token": api_token,
        "include": "scores;participants;periods;league;statistics;timeline;events;predictions;venue;lineups;referees"
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        match = response.json().get("data", {})
        print("Data:", match)
        if match:
            # Extract team names, logos, and scores
            home_team, away_team = match.get("name").split(" vs ")
            home_team_logo = match.get("participants", [])[1].get("image_path", "")
            away_team_logo = match.get("participants", [])[0].get("image_path", "")
            
            # Find the scores for home and away team
            scores = match.get("scores", [])
            home_score = "-"
            away_score = "-"
            for score in scores:
                if score.get("description") == "CURRENT":
                    if score.get("score", {}).get("participant") == "home":
                        home_score = score.get("score", {}).get("goals", "-")
                    elif score.get("score", {}).get("participant") == "away":
                        away_score = score.get("score", {}).get("goals", "-")

            context = {
                "match": match,
                "home_team": home_team,
                "away_team": away_team,
                "home_team_logo": home_team_logo,
                "away_team_logo": away_team_logo,
                "home_score": home_score,
                "away_score": away_score,
            }
            return render(request, 'livescore/team_analysis.html', context)

    return JsonResponse({'error': 'Match not found.'}, status=404)


def about_us(request):
    return render(request, 'livescore/about.html')


def privacy_policy(request):
    return render(request, 'livescore/privacy.html')


send_data_to_kafka()  # Optionally, send initial data to Kafka on server start
