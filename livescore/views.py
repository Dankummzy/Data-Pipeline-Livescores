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


def team_analysis(request, match_id):
    matches = fetch_data()
    match = None

    for m in matches:
        if m['id'] == match_id:
            match = m
            break

    if match is None:
        return JsonResponse({'error': 'Match not found.'}, status=404)

    context = {
        "competition": match["competition"],
        "season": match["season"],
        "matchday": match["matchday"],
        "stage": match["stage"],
        "group": match["group"],
        "home_team": match["homeTeam"],
        "away_team": match["awayTeam"],
        "score": match["score"],
        "referees": match["referees"],
    }

    return render(request, 'livescore/team_analysis.html', context)



def about_us(request):
    return render(request, 'livescore/about.html')

def privacy_policy(request):
    return render(request, 'livescore/privacy.html')


send_data_to_kafka()  # Optionally, send initial data to Kafka on server start
