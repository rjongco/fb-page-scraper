import traceback
from bson import ObjectId
from flask import Flask, session, render_template, request, jsonify, Response, make_response, redirect, url_for
import time, json, re, hashlib, math, sys
from flask_socketio import SocketIO, emit, call
from flask_cors import CORS 
from flask_session import Session
from cachelib.file import FileSystemCache
from urllib.parse import urlparse, urlunparse
from store import StoreController
from datetime import timedelta, datetime, timezone

from tools.Browse import facebook_post_engine, force_delete_session, generate_chrome_driver, get_engagements

store = StoreController()
app = Flask(__name__)
# app.config['SESSION_TYPE'] = 'cachelib'
# app.config['SESSION_SERIALIZATION_FORMAT'] = 'json'
# app.config['SESSION_CACHELIB'] = FileSystemCache(threshold=50, cache_dir="/sessions")
SESSION_TYPE='mongodb'
SESSION_MONGODB=store.client
SESSION_MONGODB_DB='fbps'
SESSION_MONGODB_COLLECT='session'
SECRET_KEY='90510hf031ufh0ugn02b0gu2bg02i0dj2032i'
SESSION_PERMANENT= True  # Set session to permanent
SESSION_REFRESH_EACH_REQUEST=True
PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)  # Session expiration after 30 minutes
MAX_CONCURRENT_JOB=1
MAX_TIME_SCRAPING_JOB=60*3
NEXT_JOB_COOLDOWN=60

app.config.from_object(__name__)
CORS(app)
Session(app)
socketio = SocketIO(app, cors_allowed_origins="*",manage_session=False)


def generate_data():
    for i in range(999):
        yield f"this is data{session.get('ip')}", i, False

def get_client_ip():
    if "X-Forwarded-For" in request.headers:
        return request.headers.get("X-Forwarded-For").split(',')[0]
    else:
        return request.remote_addr

def get_user_agent():
    return request.headers.get('User-Agent')

def get_referer():
    return request.headers.get("Referer")

def convert_to_mmss(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02}:{seconds:02}"

def sanitize_url(url):
    # Basic sanitation: remove any unwanted characters from the URL (e.g., whitespace)
    sanitized_url = url.strip()
    
    # You can add more specific sanitization rules depending on your needs.
    # For example, escaping certain characters, removing certain query parameters, etc.
    
    # You can also make sure it starts with "http://" or "https://"
    if not sanitized_url.startswith(('http://', 'https://')):
        sanitized_url = 'http://' + sanitized_url  # Default to 'http://' if missing
    
    return sanitized_url

def sanitize(url):
    # First, sanitize the URL
    sanitized_url = sanitize_url(url)
    
    # Parse the URL to validate it
    parsed_url = urlparse(sanitized_url)
    
    # Check if the URL has a valid scheme (http or https) and a valid netloc (domain)
    if parsed_url.scheme not in ['http', 'https']:
        return False, "Invalid scheme. Only 'http' or 'https' are allowed."
    
    if not parsed_url.netloc:  # No domain present
        return False, "Invalid URL. No domain found."
    if 'facebook.com' not in parsed_url.netloc:
        return False, "Invalid Facebook URL."
    # Optionally, check if the domain is valid (simple regex to check domain pattern)
    domain_pattern = re.compile(r'^[a-zA-Z0-9.-]+$')
    if not domain_pattern.match(parsed_url.netloc):
        return False, "Invalid domain format."

    return True, sanitized_url

@app.route('/', methods=['GET'])
def home():
    # session is unique per browser and private tabs
    # ip is unique per network machine
    ip = get_client_ip()
    session['ip'] = ip

    session_id = session.sid
    
    wait = None

    if 'status' not in session:
        session['status'] = 'standby'
        session['cooldown'] = 0
    else:
        if 'cooldown' in session['status']:
            wait = max(int(session['cooldown']) - time.time(), 0)
            if wait == 0:
                wait = None
                session['status'] = 'standby'
                session['cooldown'] = 0
        if 'queued' in session['status']:
            session['status'] = 'standby'

    store.queue.delete_many({
        "$or": [
            {"ip": ip},
            {"session": session_id}
        ]
    })

    if store.job.find_one({"ip": ip}) != None:
        store.job.delete_many({
            "$or": [
                {"ip": ip},
                {"session": session_id}
            ]
        })
        session['status'] = f'cooldown'
        session['cooldown'] = time.time() + NEXT_JOB_COOLDOWN # 5 minutes

    resp = make_response(render_template('index.html', wait=wait, status=session['status']))
    resp.set_cookie('fb-page-scraper-session', f'{session_id}')
    return resp

@app.route('/scrape', methods=['POST'])
def check_session():
        try:
            if 'cooldown' in session['status']:
                remaining = int(session['cooldown']) - int(time.time())
                if remaining > 0 :
                    raise Exception(f"Please try again in: {convert_to_mmss(remaining)}")
                raise Exception(f"Please refresh the page to continue.")
            in_job = store.job.find_one({'ip':f'{session.get("ip")}'})
            if in_job != None:
                raise Exception("Please try again later.")
            data = request.get_json()
            url = data['url'] if 'url' in data else None
            if url == None:
                raise Exception("Facebook Page URL not found.")
            
            is_url_valid, url = sanitize(url)
            if is_url_valid == False:
                raise Exception("Invalid URL.")
            
            store.queue.delete_one({'ip': session.get('ip')})
            add_queue = store.queue.insert_one({
                'ip': session.get('ip'),
                'session': session.sid,
                'url': url,
                'createdAt': datetime.now()
            })

            if add_queue.acknowledged == False:
                raise Exception("Please try again later.")
            
            q_id = str(add_queue.inserted_id)

            session['hash'] = q_id

            session['status'] = 'queued'

            return make_response({'message':'In queue', 'hash':q_id}, 200)
        except Exception as ex:
            return make_response({'message': str(ex), 'hash':None}, 500)
            pass


@socketio.on('scrape')
def scraper(data):
        job_id = None
        q_id = data['hash'] if "hash" in data else None
        inline = store.queue.find_one({'_id': ObjectId(q_id)})
        if inline == None:
            emit('error', 'Something went wrong, please try again later.')
            return False
        older_queued_jobs = store.queue.count_documents({"_id": {"$lt": inline['_id']}})
        percent_on_scraping = 40
        percent_on_queueing = 10   #40 - 10 = 30
        steps_per_item_queue = percent_on_scraping - percent_on_queueing
        steps_per_item_queue /= older_queued_jobs if older_queued_jobs > 0 else 1
        steps_per_item_queue = math.floor(steps_per_item_queue)
        # remaining_time_if_queued = (older_queued_jobs * MAX_TIME_SCRAPING_JOB)
        # current_on_the_job = store.job.count_documents({})
        # remaining_time_if_queued += MAX_TIME_SCRAPING_JOB if current_on_the_job >= MAX_CONCURRENT_JOB else 0
        # estimated_start_time = time.time() + remaining_time_if_queued
        
        is_alive = {'status': True}
        is_alive_callback = lambda x: is_alive.update(status=x)

        while True:
            if store.queue.find_one({'_id': ObjectId(inline['_id'])}) == None:
                print('client was resetted')
                emit('stream', {'log':'Session was restarted. Please reload the page.', 'percent': 0, 'completion': False}, callback=lambda x: x)
                return
            if is_alive['status'] == False:
                print('client is dead while queueing')
                store.queue.delete_one({'_id': ObjectId(inline['_id'])})
                return
            
            is_alive_callback(False)
            next_inline = store.queue.find().sort("_id", 1).limit(1)
            current_on_the_job = store.job.count_documents({})
            if inline['_id'] == next_inline[0]['_id'] and current_on_the_job < MAX_CONCURRENT_JOB:
                is_queued = store.queue.delete_one({'_id': ObjectId(inline['_id'])})
                if is_queued.deleted_count == 0:
                    emit('error', 'Something went wrong, please try again later.')
                    return False
                inserted = store.job.insert_one({
                    'ip': inline['ip'],
                    'session': inline['session'],
                    'url': inline['url'],
                    'startedAt': datetime.now()
                })
                job_id = inserted.inserted_id
                emit('stream', {'log':'Scraping . . .', 'percent': percent_on_scraping, 'completion': False}, callback=is_alive_callback)
                break
            else:
                store.queue.update_one({'_id':ObjectId(inline['id'])},
                                       {'$set':{'createdAt': datetime.now()}})
                refetch_older_queue = store.queue.count_documents({"_id": {"$lt": inline['_id']}})
                emit('stream', {'log':f'Queuing . . .', 'percent': (percent_on_queueing + (percent_on_scraping - (steps_per_item_queue * (refetch_older_queue if refetch_older_queue > 0 else 1)))), 'completion': False}, callback=is_alive_callback)

                print('waiting it on')

            time.sleep(10)

        if job_id == None:
            emit('error', 'Something went wrong, please try again later.')
            return
        
        is_alive_callback(True)
        
        _job = store.job.find_one({'_id':ObjectId(job_id)})
        _url =_job['url']
        collected_lines = []
        increment_per_second = (100 - percent_on_scraping) / MAX_TIME_SCRAPING_JOB
        for _data, _is_done, _elapsed in scraper_engine(_url):
            if store.job.find_one({'_id': ObjectId(job_id)}) == None:
                print('client was resetted')
                emit('stream', {'log':'Session was restarted. Please reload the page.', 'percent': 0, 'completion': False}, callback=lambda x: x)
                return
            if is_alive['status'] == False:
                print('client is dead while scraping')
                store.job.delete_many({'_id':ObjectId(job_id)})
                return
                
            is_alive_callback(False)

            if _is_done:
                store.job.delete_many({'_id':ObjectId(job_id)})
                emit('stream', {'log':f'Scraper completed.', 'percent':100, 'completion':True, 'data':collected_lines}, callback=is_alive_callback)
                break
            
            store.job.update_one({'_id': job_id},
                                {'$set':{'startedAt': datetime.now()}})
            collected_lines.append(_data)
          
            updated_percentage = percent_on_scraping + increment_per_second * _elapsed
            emit('stream', {'log':f'Scraping . . .', 'percent':updated_percentage, 'completion':False}, callback=is_alive_callback)

            

@socketio.on('connect')
def socket_connect(sid):
    # Place the logic from your Python script here
    print(f'Client connected: {sid}')
            

@socketio.on('disconnect')
def socket_connect(sid):
    # Place the logic from your Python script here
    print(f'Client disconnected: {sid}')


def scraper_engine(url:str):
    scannerdriver, scannersession = generate_chrome_driver()
    try:
        time_job_started = None
        for _link, _type, _unix in facebook_post_engine(scannerdriver, url):
            
            data = {
                'post link': _link,
                'date posted': None,
                'category': _type
            }
            if _unix != None:
                data['date posted'] = datetime.fromtimestamp(_unix, tz=timezone.utc).strftime('%d %B %Y %I:%M %p')
            if time_job_started == None:
                time_job_started = time.time()
            elapsed = (time.time() - time_job_started)
            if elapsed >= MAX_TIME_SCRAPING_JOB:
                break
            yield data, False, elapsed           

    except Exception as exc:
        # raise exc
        print(f'exception in engine {str(exc)}', flush=True)
        print(f'stack trace', traceback.format_exc())
        pass
    finally:
        scannerdriver.quit()
        force_delete_session(scannersession)
    
    yield None, True, None #finished

if __name__ == '__main__':
    app.run(debug=True)