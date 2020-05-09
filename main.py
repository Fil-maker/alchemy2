from flask import Flask, render_template, url_for
from flask_login import LoginManager, login_user, login_required, logout_user
from werkzeug.utils import redirect
from wtforms import PasswordField, BooleanField, SubmitField, StringField
from wtforms.fields.html5 import IntegerField, DateField, EmailField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired

from data import db_session
from data.jobs import Jobs
from data.users import User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id)


class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    surname = StringField('Фамилия', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    submit = SubmitField('Создать')


class JobAddForm(FlaskForm):
    team_leader = EmailField('Почта тимлида', validators=[DataRequired()])
    job = StringField('Название работы', validators=[DataRequired()])
    work_size = IntegerField('Количество часов работы', validators=[DataRequired()])
    collaborators = EmailField('Почта соучастника', validators=[DataRequired()])
    end_date = DateField('Предположительное время конца работы', validators=[DataRequired()])
    is_finished = BooleanField('Закончена ли работа?')
    submit = SubmitField('Создать')


class JobChangeForm(FlaskForm):
    work_size = IntegerField('Размер работы')
    collaborators = EmailField('Почта соучастника')
    end_date = DateField('Предположительное время конца работы')
    is_finished = BooleanField('Закончена ли работа?')
    submit = SubmitField('Изменить')


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            surname=form.surname.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        login_user(user)
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/')
def start():
    session = db_session.create_session()
    name, team_leader, duration, team_id, finished = [], [], [], [], []
    for job in session.query(Jobs).all():
        leader = session.query(User).filter(User.id == job.team_leader).first()
        collaborators = job.collaborators.split()
        team_col = []
        for col in collaborators:
            cold = session.query(User).filter(User.email == col).first()
            team_col.append(cold)

        name.append(job.job)
        team_leader.append(leader)
        duration.append(job.work_size)
        team_id.append(team_col)
        finished.append(job.is_finished)
    return render_template('main.html', count=len(name), style=url_for('static', filename='css/style.css'), name=name,
                           team_leader=team_leader, duration=duration, team_id=team_id, finished=finished)


@app.route('/job_add', methods=['GET', 'POST'])
def job_add():
    form = JobAddForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        if session.query(Jobs).filter(Jobs.job == form.job.data).first():
            return render_template('job.html', title='Создание проекта', form=form,
                                   message='Проект с таким названием уже существует')
        lead = session.query(User).filter(User.email == form.team_leader.data).first()
        if session.query(User).filter(User.email == form.team_leader.data).first() is None:
            return render_template('job.html', title='Создание проекта', form=form,
                                   message='Пользователя-тимлида с такой почтой нет')
        col = session.query(User).filter(User.email == form.collaborators.data).first()
        if session.query(User).filter(User.email == form.collaborators.data).first() is None:
            return render_template('job.html', title='Создание проекта', form=form,
                                   message='Пользователя-соучастника с такой почтой нет')
        if lead.email == col.email:
            return render_template('job.html', title='Создание проекта', form=form,
                                   message='Пользователь-соучастник не должен быть тимлидом')
        job = Jobs(
            team_leader=lead.id,
            job=form.job.data,
            collaborators=form.collaborators.data,
            work_size=form.work_size.data,
        )
        session.add(job)
        session.commit()
        return redirect('/')
    return render_template('job.html', title='Создание проекта', form=form)


@login_required
@app.route('/<int:user_id>/job/edit/<string:job_name>', methods=['GET', 'POST'])
def edit_job(user_id, job_name):
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    project = session.query(Jobs).filter(Jobs.job == job_name).first()
    if user.id == project.team_leader or user.id == 1:
        form = JobChangeForm()
        if form.validate_on_submit():
            work_size = form.work_size.data
            collaborators = form.collaborators.data
            end_date = form.end_date.data
            is_finished = form.is_finished.data
            if work_size:
                project.work_size = work_size
            if collaborators:
                project.collaborators = collaborators
            if end_date:
                project.end_date = end_date
            if is_finished:
                project.is_finished = is_finished
            session.commit()
            return redirect('/')
        return render_template('postjob.html', form=form)
    return redirect('/')


@login_required
@app.route('/<int:user_id>/job/delete/<string:job_name>')
def delete_job(user_id, job_name):
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    project = session.query(Jobs).filter(Jobs.job == job_name).first()
    if user.id == project.team_leader or user.id == 1:
        session.delete(project)
        session.commit()
    return redirect('/')


def main():
    db_session.global_init("db/blogs.sqlite")
    app.run()


if __name__ == '__main__':
    main()
