from flask import Flask, render_template, request, jsonify, session
from services.s3_service import S3Service
from services.generator_service import GeneratorService
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = 'super_secret_agent_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Services
s3_svc = S3Service()
gen_svc = GeneratorService()

# In-memory "Database" for the session state
# Structure: { session_id: { phase: 1, data: {...} } }
workflow_state = {}

def get_state(sid):
    if sid not in workflow_state:
        workflow_state[sid] = {
            'phase': 1,
            'ref_image': None,
            'bg_image': None,
            'angle_image': None,
            'gen_image': None,
            'prompt': "A futuristic bananas in neon style", # Default prompt
            'history': []
        }
    return workflow_state[sid]

@app.route('/')
def index():
    # Assign a session ID if not present
    if 'uid' not in session:
        session['uid'] = str(uuid.uuid4())
    
    sid = session['uid']
    state = get_state(sid)
    
    # Auto-start Phase 1 if empty
    if state['phase'] == 1 and not state['ref_image']:
        state['ref_image'] = s3_svc.get_reference_image()
        # Move to Phase 2 automatically after getting ref
        state['phase'] = 2
        
    return render_template('index.html')

@app.route('/api/status')
def status():
    sid = session.get('uid')
    if not sid:
        return jsonify({'error': 'No session'}), 403
    return jsonify(get_state(sid))

@app.route('/api/upload', methods=['POST'])
def upload_files():
    sid = session.get('uid')
    state = get_state(sid)
    
    if state['phase'] != 2:
        return jsonify({'error': 'Not in Phase 2'}), 400

    bg = request.files.get('background')
    angle = request.files.get('angle')
    
    if bg:
        path = os.path.join(app.config['UPLOAD_FOLDER'], f"{sid}_bg_{bg.filename}")
        bg.save(path)
        state['bg_image'] = path
        
    if angle:
        path = os.path.join(app.config['UPLOAD_FOLDER'], f"{sid}_angle_{angle.filename}")
        angle.save(path)
        state['angle_image'] = path
    
    # If both uploaded, trigger Phase 3
    if state['bg_image'] and state['angle_image']:
        state['phase'] = 3
        # In a real app, use Celery/Queue. Here we block or use a flag to poll creation.
        # We'll rely on the /api/generate endpoint to actually trigger the work async-ish
        # or just client calls it next.
        
    return jsonify({'status': 'uploaded'})

@app.route('/api/generate', methods=['POST'])
def generate():
    sid = session.get('uid')
    state = get_state(sid)
    
    if state['phase'] != 3:
        return jsonify({'error': 'Not in Phase 3'}), 400
        
    # Generate
    img_url = gen_svc.generate_image(
        state['prompt'],
        state['ref_image'],
        state['bg_image'],
        state['angle_image']
    )
    
    state['gen_image'] = img_url
    state['phase'] = 4 # Evaluation
    
    return jsonify({'status': 'generated', 'image_url': img_url})

@app.route('/api/feedback', methods=['POST'])
def feedback():
    sid = session.get('uid')
    state = get_state(sid)
    
    if state['phase'] != 4:
        return jsonify({'error': 'Not in Phase 4'}), 400
        
    data = request.json
    action = data.get('action') # 'approve' or 'reject'
    
    if action == 'approve':
        # Upload to S3
        gen_image_path = state['gen_image']
        if gen_image_path.startswith('/static/'):
            local_path = gen_image_path[1:]  # Remove leading slash
        else:
            local_path = gen_image_path
        
        filename = os.path.basename(local_path)
        s3_url = s3_svc.upload_approved_image(local_path, filename)
        state['approved_s3_url'] = s3_url
        state['phase'] = 6 # Done
    elif action == 'reject':
        new_prompt = data.get('prompt')
        state['prompt'] = new_prompt
        state['history'].append(state['gen_image'])
        state['phase'] = 3 # Go back to Generation
    
    return jsonify({'status': 'updated'})

@app.route('/api/reset', methods=['POST'])
def reset():
    sid = session.get('uid')
    if sid in workflow_state:
        del workflow_state[sid]
    return jsonify({'status': 'reset'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
