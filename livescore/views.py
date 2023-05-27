import json
import requests
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
import threading

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


def consume_messages():
    with consumer_lock:
        for message in consumer:
            yield 'data: {}\n\n'.format(json.dumps(message.value))


def fetch_data():
    uri = 'https://api.football-data.org/v4/matches'
    headers = {'X-Auth-Token': '13224ed623424ea4a72fb5d6c0622e0d'}

    response = requests.get(uri, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data['matches']
    else:
        print('Failed to fetch data from the API:', response.content)
        return []


def send_data_to_kafka():
    matches = fetch_data()
    for match in matches:
        producer.send(TOPIC_NAME, value=match)
        producer.flush()


def livescores(request):
    return StreamingHttpResponse(consume_messages(), content_type='text/event-stream')


def get_matches(request):
    api_url = 'https://api.football-data.org/v4/matches'
    headers = {'X-Auth-Token': '13224ed623424ea4a72fb5d6c0622e0d'}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        matches = response.json()['matches']
        context = {'matches': matches}
        return render(request, 'livescore/matches.html', context)
    else:
        return JsonResponse({'error': 'Failed to fetch matches.'}, status=response.status_code)


def team_analysis(request):
    data = {
        "area": {"id": 2220, "name": "South America", "code": "SAM", "flag": "https://crests.football-data.org/CLI.svg"},
        "competition": {"id": 2152, "name": "Copa Libertadores", "code": "CLI", "type": "CUP", "emblem": "https://crests.football-data.org/CLI.svg"},
        "season": {"id": 1545, "startDate": "2023-02-08", "endDate": "2023-11-11", "currentMatchday": 4, "winner": None},
        "status": "FINISHED",
        "matchday": 4,
        "stage": "GROUP_STAGE",
        "group": "GROUP_A",
        "homeTeam": {"id": 9362, "name": "CD Nublense", "shortName": "Nublense", "tla": "CDN", "crest": "https://crests.football-data.org/9362.png"},
        "awayTeam": {"id": 1783, "name": "CR Flamengo", "shortName": "Flamengo", "tla": "FLA", "crest": "https://crests.football-data.org/1783.png"},
        "score": {"winner": "DRAW", "duration": "REGULAR", "fullTime": {"home": 1, "away": 1}, "halfTime": {"home": 0, "away": 1}},
        "referees": []
    }

    context = {
        "competition": data["competition"],
        "season": data["season"],
        "matchday": data["matchday"],
        "stage": data["stage"],
        "group": data["group"],
        "home_team": data["homeTeam"]["name"],
        "away_team": data["awayTeam"],
        "score": data["score"],
        "referees": data["referees"],
    }

    return render(request, 'livescore/team_analysis.html', context)


def about_us(request):
    return render(request, 'livescore/about.html')

def privacy_policy(request):
    return render(request, 'livescore/privacy.html')


send_data_to_kafka()  # Optionally, send initial data to Kafka on server start
