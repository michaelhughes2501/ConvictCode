from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, CSRFError
from wtforms import StringField, PasswordField, TextAreaField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from database import db, User, Message, ForumPost, ForumComment, Like, Match

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///felon_dating.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class ProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[Length(max=50)])
    last_name = StringField('Last Name', validators=[Length(max=50)])
    age = IntegerField('Age', validators=[NumberRange(min=18, max=120)], render_kw={'placeholder': 'Your age'})
    gender = SelectField('Gender', choices=[('', 'Select'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    location = StringField('Location', validators=[Length(max=100)])
    bio = TextAreaField('Bio', validators=[Length(max=500)])
    crime_type = StringField('Offense Type', validators=[Length(max=100)])
    release_date = StringField('Release Date', validators=[Length(max=50)])
    rehabilitation_status = SelectField('Rehabilitation Status', choices=[
        ('', 'Select'),
        ('Completed Program', 'Completed Program'),
        ('In Progress', 'In Progress'),
        ('Seeking Support', 'Seeking Support')
    ])
    looking_for = StringField('Looking For', validators=[Length(max=100)])

class ForumPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('General', 'General Discussion'),
        ('Support', 'Support & Advice'),
        ('Success Stories', 'Success Stories'),
        ('Resources', 'Resources & Information')
    ])

class MessageForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=1000)])

# Static resource directory
RESOURCES = [
    {'category': 'Housing', 'name': 'National Reentry Resource Center', 'description': 'Federal housing and transitional resources after incarceration', 'url': '#', 'tags': ['housing', 'federal', 'reentry']},
    {'category': 'Housing', 'name': 'Volunteers of America', 'description': 'Transitional housing, shelter, and long-term support services', 'url': '#', 'tags': ['housing', 'transitional', 'support']},
    {'category': 'Housing', 'name': 'Fair Housing Act Resources', 'description': 'Know your rights when renting with a criminal record', 'url': '#', 'tags': ['housing', 'legal', 'rights', 'fair housing']},
    {'category': 'Employment', 'name': 'American Job Centers', 'description': 'Free job training, resume help, and placement services nationwide', 'url': '#', 'tags': ['jobs', 'training', 'resume', 'employment']},
    {'category': 'Employment', 'name': 'Honest Jobs', 'description': 'Job board specifically for people with conviction records', 'url': '#', 'tags': ['jobs', 'fair-chance', 'employment']},
    {'category': 'Employment', 'name': 'Ban the Box Campaign', 'description': 'Directory of fair-chance employers who don\'t ask about records upfront', 'url': '#', 'tags': ['jobs', 'fair-chance', 'ban the box', 'hiring']},
    {'category': 'Legal Aid', 'name': 'Legal Aid Society', 'description': 'Free civil legal services for individuals who qualify by income', 'url': '#', 'tags': ['legal', 'aid', 'civil', 'free']},
    {'category': 'Legal Aid', 'name': 'Expungement Clinics', 'description': 'Record clearing and expungement assistance in your area', 'url': '#', 'tags': ['legal', 'expungement', 'record', 'clearing']},
    {'category': 'Legal Aid', 'name': 'Reentry Rights Coalition', 'description': 'Know your voting, housing, and employment rights after release', 'url': '#', 'tags': ['legal', 'rights', 'voting', 'reentry']},
    {'category': 'Mental Health', 'name': 'SAMHSA Helpline', 'description': '24/7 mental health and substance use helpline — call 1-800-662-4357', 'url': '#', 'tags': ['mental health', 'substance', 'helpline', 'crisis', '24/7']},
    {'category': 'Mental Health', 'name': 'NAMI Support Groups', 'description': 'Free peer-led mental health support groups nationwide', 'url': '#', 'tags': ['mental health', 'support group', 'community', 'free']},
    {'category': 'Mental Health', 'name': 'Crisis Text Line', 'description': 'Text HOME to 741741 for free 24/7 crisis counseling', 'url': '#', 'tags': ['mental health', 'crisis', '24/7', 'text']},
    {'category': 'Education', 'name': 'Second Chance Pell Grants', 'description': 'Federal education grants available to formerly incarcerated individuals', 'url': '#', 'tags': ['education', 'college', 'pell', 'grant', 'free']},
    {'category': 'Education', 'name': 'GED Testing Service', 'description': 'High school equivalency preparation resources and testing centers', 'url': '#', 'tags': ['education', 'ged', 'diploma', 'high school']},
    {'category': 'Education', 'name': 'Vocational Training Programs', 'description': 'Hands-on trade and career certification programs for reentrants', 'url': '#', 'tags': ['education', 'vocational', 'trade', 'certification']},
    {'category': 'Community', 'name': 'Alcoholics Anonymous', 'description': '12-step recovery community with meetings worldwide — free to attend', 'url': '#', 'tags': ['recovery', 'alcohol', 'community', 'support', 'free']},
    {'category': 'Community', 'name': 'Narcotics Anonymous', 'description': 'Peer support community for people in recovery from drug addiction', 'url': '#', 'tags': ['recovery', 'drugs', 'community', 'support', 'free']},
    {'category': 'Community', 'name': 'Mentoring for Reentry', 'description': 'One-on-one mentorship programs connecting you with community guides', 'url': '#', 'tags': ['mentoring', 'community', 'support', 'guidance']},
]

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        if existing_user:
            flash('Username or email already exists.', 'danger')
            return render_template('register.html', form=form)
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    matches = Match.query.filter(
        ((Match.user1_id == current_user.id) | (Match.user2_id == current_user.id)) &
        (Match.is_mutual == True)
    ).limit(5).all()
    unread_messages = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    recent_posts = ForumPost.query.order_by(ForumPost.created_at.desc()).limit(5).all()
    potential_matches = Like.query.filter_by(liked_user_id=current_user.id).all()
    return render_template('dashboard.html',
                           matches=matches,
                           unread_messages=unread_messages,
                           recent_posts=recent_posts,
                           potential_matches=potential_matches)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        form.populate_obj(current_user)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', form=form, user=current_user)

@app.route('/profile/<int:user_id>')
@login_required
def view_profile(user_id):
    user = User.query.get_or_404(user_id)
    is_match = Match.query.filter(
        ((Match.user1_id == current_user.id) & (Match.user2_id == user_id)) |
        ((Match.user1_id == user_id) & (Match.user2_id == current_user.id))
    ).first()
    has_liked = Like.query.filter_by(user_id=current_user.id, liked_user_id=user_id).first()
    return render_template('view_profile.html', user=user, is_match=is_match, has_liked=has_liked)

@app.route('/like/<int:user_id>', methods=['POST'])
@login_required
def like_user(user_id):
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot like yourself'}), 400
    existing_like = Like.query.filter_by(user_id=current_user.id, liked_user_id=user_id).first()
    if existing_like:
        return jsonify({'error': 'Already liked this user'}), 400
    like = Like(user_id=current_user.id, liked_user_id=user_id)
    db.session.add(like)
    mutual_like = Like.query.filter_by(user_id=user_id, liked_user_id=current_user.id).first()
    if mutual_like:
        match = Match(user1_id=min(current_user.id, user_id),
                      user2_id=max(current_user.id, user_id),
                      is_mutual=True)
        db.session.add(match)
    db.session.commit()
    return jsonify({'success': True, 'mutual': bool(mutual_like)})

@app.route('/messages')
@login_required
def messages():
    sent_conversations = db.session.query(Message.recipient_id).filter_by(sender_id=current_user.id).distinct()
    received_conversations = db.session.query(Message.sender_id).filter_by(recipient_id=current_user.id).distinct()
    user_ids = set()
    for conv in sent_conversations:
        user_ids.add(conv[0])
    for conv in received_conversations:
        user_ids.add(conv[0])
    conversations = []
    for uid in user_ids:
        user = User.query.get(uid)
        last_message = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == uid)) |
            ((Message.sender_id == uid) & (Message.recipient_id == current_user.id))
        ).order_by(Message.created_at.desc()).first()
        unread_count = Message.query.filter_by(sender_id=uid, recipient_id=current_user.id, is_read=False).count()
        conversations.append({'user': user, 'last_message': last_message, 'unread_count': unread_count})
    conversations.sort(key=lambda x: x['last_message'].created_at if x['last_message'] else datetime.min, reverse=True)
    return render_template('messages.html', conversations=conversations)

@app.route('/messages/<int:user_id>', methods=['GET', 'POST'])
@login_required
def conversation(user_id):
    other_user = User.query.get_or_404(user_id)
    form = MessageForm()
    Message.query.filter_by(sender_id=user_id, recipient_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    if form.validate_on_submit():
        message = Message(sender_id=current_user.id, recipient_id=user_id, message=form.message.data)
        db.session.add(message)
        db.session.commit()
        return redirect(url_for('conversation', user_id=user_id))
    messages_list = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.created_at).all()
    return render_template('conversation.html', other_user=other_user, messages=messages_list, form=form)

@app.route('/forum')
def forum():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', 'all')
    query = ForumPost.query
    if category != 'all':
        query = query.filter_by(category=category)
    posts = query.order_by(ForumPost.created_at.desc()).paginate(page=page, per_page=10)
    categories = ['General', 'Support', 'Success Stories', 'Resources']
    return render_template('forum.html', posts=posts, categories=categories, current_category=category)

@app.route('/forum/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = ForumPostForm()
    if form.validate_on_submit():
        post = ForumPost(user_id=current_user.id, title=form.title.data,
                         content=form.content.data, category=form.category.data)
        db.session.add(post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('view_post', post_id=post.id))
    return render_template('new_post.html', form=form)

@app.route('/forum/post/<int:post_id>')
def view_post(post_id):
    post = ForumPost.query.get_or_404(post_id)
    post.views += 1
    db.session.commit()
    comments = ForumComment.query.filter_by(post_id=post_id).order_by(ForumComment.created_at).all()
    return render_template('view_post.html', post=post, comments=comments)

@app.route('/forum/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content')
    if content:
        comment = ForumComment(post_id=post_id, user_id=current_user.id, content=content)
        db.session.add(comment)
        db.session.commit()
        flash('Comment added!', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/matches')
@login_required
def matches():
    user_matches = Match.query.filter(
        ((Match.user1_id == current_user.id) | (Match.user2_id == current_user.id)) &
        (Match.is_mutual == True)
    ).all()
    match_users = []
    for match in user_matches:
        other_user = match.user2 if match.user1_id == current_user.id else match.user1
        match_users.append(other_user)
    return render_template('matches.html', matches=match_users)

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    min_age = request.args.get('min_age', type=int)
    max_age = request.args.get('max_age', type=int)
    location = request.args.get('location', '')
    users_query = User.query.filter(User.id != current_user.id)
    if query:
        users_query = users_query.filter(
            (User.username.contains(query)) |
            (User.first_name.contains(query)) |
            (User.last_name.contains(query))
        )
    if min_age:
        users_query = users_query.filter(User.age >= min_age)
    if max_age:
        users_query = users_query.filter(User.age <= max_age)
    if location:
        users_query = users_query.filter(User.location.contains(location))
    users = users_query.limit(50).all()
    return render_template('search.html', users=users, query=query)

@app.route('/resources')
def resources_page():
    categories = sorted({r['category'] for r in RESOURCES})
    return render_template('resources.html', resources=RESOURCES, categories=categories)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# API routes

@app.route('/api/chat', methods=['POST'])
@login_required
@csrf.exempt
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=400,
            system=(
                "You are a warm, compassionate support assistant for SecondChance Connect — "
                "a community platform for individuals with past convictions seeking rehabilitation, "
                "meaningful connections, and a fresh start. "
                "Help users with: finding housing, employment opportunities, legal aid, expungement, "
                "mental health resources, platform features, and general encouragement. "
                "Keep responses concise (2-4 sentences), warm, and practical. "
                "Never give specific legal advice. Always encourage professional consultation for legal matters."
            ),
            messages=[{'role': 'user', 'content': user_message}]
        )
        reply = response.content[0].text
    except Exception:
        reply = (
            "I'm here to help! I can point you toward housing resources, employment programs, "
            "legal aid, mental health support, and help you navigate this platform. "
            "Check the Resources page for a full directory, or ask me a specific question."
        )
    return jsonify({'reply': reply})

@app.route('/api/analytics')
@login_required
def analytics():
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    return jsonify({
        'total_users': User.query.count(),
        'total_messages': Message.query.count(),
        'total_posts': ForumPost.query.count(),
        'total_matches': Match.query.filter_by(is_mutual=True).count(),
        'new_users_week': User.query.filter(User.created_at >= week_ago).count(),
        'messages_week': Message.query.filter(Message.created_at >= week_ago).count(),
        'posts_week': ForumPost.query.filter(ForumPost.created_at >= week_ago).count(),
    })

@app.route('/api/resources')
def resources_api():
    query = request.args.get('q', '').lower()
    category = request.args.get('category', '').lower()
    results = RESOURCES
    if query:
        results = [r for r in results
                   if query in r['name'].lower() or
                   query in r['description'].lower() or
                   any(query in tag for tag in r['tags'])]
    if category:
        results = [r for r in results if r['category'].lower() == category]
    return jsonify(results)

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash('Security token expired. Please try again.', 'danger')
    return redirect(request.referrer or url_for('index'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', '0').lower() in ('1', 'true', 'yes', 'on')
    app.run(host=host, port=port, debug=debug)
