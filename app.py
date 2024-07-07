import requests
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
socketio = SocketIO(app)

# Dictionary to keep track of clients and their URLs
clients = {}

def get_domain_info(url):
    try:
        response = requests.get(f"https://ipinfo.io/{url}/json")
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': 'Failed to fetch domain info'}
    except Exception as e:
        return {'error': str(e)}


# Helper function to get subdomains
def get_subdomains(domain):
    response = requests.get(f"https://subdomains.whoisxmlapi.com/api/v1?apiKey=YOUR_API_KEY&domainName={domain}")
    data = response.json()
    return data.get("subdomains", [])

# Helper function to fetch asset domains
def fetch_asset_domains(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    assets = {
        "javascripts": [script['src'] for script in soup.find_all('script') if 'src' in script.attrs],
        "stylesheets": [link['href'] for link in soup.find_all('link', rel='stylesheet') if 'href' in link.attrs],
        "images": [img['src'] for img in soup.find_all('img') if 'src' in img.attrs],
        "iframes": [iframe['src'] for iframe in soup.find_all('iframe') if 'src' in iframe.attrs],
        "anchors": [a['href'] for a in soup.find_all('a') if 'href' in a.attrs]
    }
    
    return assets

# Route to analyze website
@app.route('/')
def analyze_website():
    url = request.args.get('url', 'https://google.com')  # Default to google.com if 'url' is not provided
    print(f"Received URL: {url}")  # Debugging statement
    
    domain_info = get_domain_info(url)
    subdomains = get_subdomains(url)
    asset_domains = fetch_asset_domains(url)
    return jsonify({
        "info": domain_info,
        "subdomains": subdomains,
        "asset_domains": asset_domains
    })

# WebSocket endpoint
@socketio.on('message')
def handle_message(data):
    print('received message: ' + data)
    if 'url' in data:
        url = data['url']
        clients[request.sid] = url
        emit('response', {'data': f'session created for {url}'})
    elif 'operation' in data:
        operation = data['operation']
        url = clients.get(request.sid)
        if operation == 'get_info':
            domain_info = get_domain_info(url)
            emit('response', {'data': domain_info})
        elif operation == 'get_subdomains':
            subdomains = get_subdomains(url)
            emit('response', {'data': subdomains})
        elif operation == 'get_asset_domains':
            asset_domains = fetch_asset_domains(url)
            emit('response', {'data': asset_domains})
        else:
            emit('response', {'data': 'Invalid operation'})

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    clients.pop(request.sid, None)
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, debug=True)
