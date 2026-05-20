from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange
from datetime import datetime
import os
from dotenv import load_dotenv
from database import db, User, Message, ForumPost, ForumComment, Like, Match

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///felon_dating.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    age = IntegerField('Age', validators=[NumberRange(min=18, max=120)])
    gender = SelectField('Gender', choices=[('', 'Select'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    location = StringField('Location', validators=[Length(max=100)])
    bio = TextAreaField('Bio', validators=[Length(max=500)])
    crime_type = StringField('Crime Type', validators=[Length(max=100)])
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
        existing_user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
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
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    # Get recent matches
    matches = Match.query.filter(
        ((Match.user1_id == current_user.id) | (Match.user2_id == current_user.id)) &
        (Match.is_mutual == True)
    ).limit(5).all()
    
    # Get unread messages
    unread_messages = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    
    # Get recent forum posts
    recent_posts = ForumPost.query.order_by(ForumPost.created_at.desc()).limit(5).all()
    
    # Get potential matches (users who liked current user)
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
    
    # Check if it's a match (mutual like)
    mutual_like = Like.query.filter_by(user_id=user_id, liked_user_id=current_user.id).first()
    if mutual_like:
        match = Match(user1_id=min(current_user.id, user_id), 
                     user2_id=max(current_user.id, user_id), 
                     is_mutual=True)
        db.session.add(match)
        flash('It\'s a match! You can now message each other.', 'success')
    
    db.session.commit()
    return jsonify({'success': True, 'mutual': bool(mutual_like)})

@app.route('/messages')
@login_required
def messages():
    # Get all conversations
    sent_conversations = db.session.query(Message.recipient_id).filter_by(sender_id=current_user.id).distinct()
    received_conversations = db.session.query(Message.sender_id).filter_by(recipient_id=current_user.id).distinct()
    
    user_ids = set()
    for conv in sent_conversations:
        user_ids.add(conv[0])
    for conv in received_conversations:
        user_ids.add(conv[0])
    
    conversations = []
    for user_id in user_ids:
        user = User.query.get(user_id)
        last_message = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) |
            ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
        ).order_by(Message.created_at.desc()).first()
        
        unread_count = Message.query.filter_by(sender_id=user_id, recipient_id=current_user.id, is_read=False).count()
        
        conversations.append({
            'user': user,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    conversations.sort(key=lambda x: x['last_message'].created_at if x['last_message'] else datetime.min, reverse=True)
    
    return render_template('messages.html', conversations=conversations)

@app.route('/messages/<int:user_id>', methods=['GET', 'POST'])
@login_required
def conversation(user_id):
    other_user = User.query.get_or_404(user_id)
    form = MessageForm()
    
    # Mark messages as read
    Message.query.filter_by(sender_id=user_id, recipient_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    
    if form.validate_on_submit():
        message = Message(sender_id=current_user.id, recipient_id=user_id, message=form.message.data)
        db.session.add(message)
        db.session.commit()
        flash('Message sent!', 'success')
        return redirect(url_for('conversation', user_id=user_id))
    
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.created_at).all()
    
    return render_template('conversation.html', other_user=other_user, messages=messages, form=form)

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
        post = ForumPost(
            user_id=current_user.id,
            title=form.title.data,
            content=form.content.data,
            category=form.category.data
        )
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
    matches = Match.query.filter(
        ((Match.user1_id == current_user.id) | (Match.user2_id == current_user.id)) &
        (Match.is_mutual == True)
    ).all()
    
    match_users = []
    for match in matches:
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

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# Create tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)