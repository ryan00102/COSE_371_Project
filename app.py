from flask import Flask,session, render_template, request, redirect, url_for
import psycopg2

app = Flask(__name__)
connect = psycopg2.connect("dbname=movie_review_db user=postgres password=ryan0102")
cur = connect.cursor()
app.secret_key = 'secret_key'

@app.route('/')
def main():
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def handle_login_signup():
    id = request.form["id"]
    password = request.form["password"]
    role = 'admin' if password == '0000' else 'user'
    send = request.form["send"]

    # ID와 비밀번호의 최소 길이 확인
    if len(id) < 1 or len(password) < 1:
        return render_template("login.html", error="ID와 비밀번호는 최소 1글자 이상이어야 합니다.")

    if send == "sign up":
        cur.execute("SELECT * FROM users WHERE id = %s;", (id,))
        existing_user = cur.fetchone()
        if existing_user:
            return render_template("login.html", error="이미 존재하는 사용자 ID입니다.")
        else:
            cur.execute("INSERT INTO users (id, password, role) VALUES (%s, %s, %s);", (id, password, role))
            connect.commit()
            return render_template("login.html", message="회원가입이 성공적으로 완료되었습니다. 로그인해주세요.")

    elif send == "sign in":
        cur.execute("SELECT id FROM users WHERE id = %s AND password = %s;", (id, password))
        user = cur.fetchone()

        if user:
            # 로그인 성공, 메인 페이지로 이동
            session['user_id'] = id
            cur.execute(
                "SELECT m.title, m.director, m.genre, COALESCE(CAST(ROUND(AVG(r.ratings), 1) AS VARCHAR), 'None') AS avg_ratings, m.rel_date FROM movies m LEFT JOIN reviews r ON m.id = r.mid GROUP BY m.title, m.director, m.genre, m.rel_date ORDER BY m.rel_date DESC;")
            movies = cur.fetchall()
            cur.execute(
                "SELECT ratings, users.id, title, review, rev_time FROM reviews, users, movies where mid = movies.id and uid = users.id order by rev_time desc;")
            reviews = cur.fetchall()

            return render_template("main.html", movies=movies, reviews=reviews, user_id=user[0])

        else:
            return render_template("login.html", error="ID 또는 비밀번호가 잘못되었습니다.")

    return "Invalid request"

@app.route('/main', methods=['GET','POST'])
def load_main():
    user_id = session['user_id']
    movie_sort_order = request.args.get('movie_sort', 'latest')
    review_sort_order = request.args.get('review_sort', 'latest')
    if movie_sort_order == 'latest':
        cur.execute("SELECT m.title, m.director, m.genre, COALESCE(CAST(ROUND(AVG(r.ratings), 1) AS VARCHAR), 'None') AS avg_ratings, m.rel_date FROM movies m LEFT JOIN reviews r ON m.id = r.mid GROUP BY m.title, m.director, m.genre, m.rel_date ORDER BY m.rel_date DESC;")
    elif movie_sort_order == 'genre':
        cur.execute(
            "SELECT m.title, m.director, m.genre, COALESCE(CAST(ROUND(AVG(r.ratings), 1) AS VARCHAR), 'None') AS avg_ratings, m.rel_date FROM movies m LEFT JOIN reviews r ON m.id = r.mid GROUP BY m.title, m.director, m.genre, m.rel_date ORDER BY m.genre;")
    elif movie_sort_order == 'ratings':
        cur.execute(
            "SELECT m.title, m.director, m.genre, COALESCE(CAST(ROUND(AVG(r.ratings), 1) AS VARCHAR), 'None') AS avg_ratings, m.rel_date FROM movies m LEFT JOIN reviews r ON m.id = r.mid GROUP BY m.title, m.director, m.genre, m.rel_date ORDER BY avg_ratings DESC;")
    movies = cur.fetchall()

    if review_sort_order == 'latest':
        cur.execute(
            "SELECT ratings, users.id, title, review, rev_time FROM reviews, users, movies where mid = movies.id and uid = users.id order by rev_time desc;")
    elif review_sort_order == 'title':
        cur.execute(
            "SELECT ratings, users.id, title, review, rev_time FROM reviews, users, movies where mid = movies.id and uid = users.id order by genre;")
    elif review_sort_order == 'followers':
        cur.execute(
            "SELECT r.ratings,  u.id,m.title, r.review, r.rev_time, COALESCE(f.follower_count, 0) as follower_count FROM reviews r JOIN users u ON u.id = r.uid JOIN movies m ON m.id = r.mid LEFT JOIN (SELECT opid, COUNT(*) as follower_count FROM ties WHERE tie = 'follow' GROUP BY opid) f ON r.uid = f.opid ORDER BY f.follower_count, r.rev_time DESC;")

    reviews = cur.fetchall()
    return render_template("main.html",movies=movies, reviews=reviews, user_id=user_id)

@app.route('/movie_info/<title>')
def movie_info(title):
    # 영화 기본 정보 조회
    cur.execute("SELECT id, title, director, genre, rel_date FROM movies WHERE title = %s", (title,))
    movie_details = cur.fetchall()

    # 해당 영화의 리뷰 조회
    cur.execute("SELECT r.ratings, u.id AS reviewer, r.review, r.rev_time FROM movies m JOIN reviews r ON m.id = r.mid JOIN users u ON u.id = r.uid WHERE m.title = %s", (title,))
    reviews = cur.fetchall()
    cur.execute("SELECT r.ratings FROM movies m JOIN reviews r ON m.id = r.mid JOIN users u ON u.id = r.uid WHERE m.title = %s", (title,))
    ratings = cur.fetchall()
    s= 0
    for i in ratings:
        s += i[0]
    avg_ratings =  round(s/len(ratings),1) if len(ratings) >=1 else None

    return render_template('movie_info.html', login_id = session['user_id'], movie=movie_details, reviews=reviews, rating = avg_ratings)


@app.route('/user_info/<name>')
def user_info(name):

    cur.execute(
        "SELECT role FROM users where id = %s",(name,))
    role = cur.fetchall()
    isMe = False
    if name == session['user_id']:
        isMe = True
    else:
        isMe = False
    cur.execute("SELECT r.ratings, m.title, r.review, r.rev_time FROM reviews r JOIN movies m ON r.mid = m.id WHERE r.uid = '{}';".format(name))
    reviews = cur.fetchall()
    cur.execute("SELECT id FROM ties WHERE opid = '{}' AND tie = 'follow';".format(name))
    followers = cur.fetchall()

    cur.execute("SELECT opid FROM ties WHERE id = '{}' AND tie = 'mute';".format(name))
    muted_users = cur.fetchall()
    cur.execute("SELECT opid AS Followed_User_ID FROM ties WHERE id = '{}' AND tie = 'follow';".format(name))
    following_users= cur.fetchall()
    return render_template('user_info.html', role = role[0][0], login_id = session['user_id'],id=name, isMe = isMe,reviews = reviews,followers = followers, muted_users = muted_users, following_users = following_users)


@app.route('/submit-review/<movie_id>', methods=['POST'])
def submit_review(movie_id):
    score = request.form['score']
    content = request.form['content']
    user_id = session['user_id']  # 현재 사용자 ID, 로그인 시스템을 통해 얻어야 함
    movie_id = movie_id  # 현재 리뷰하는 영화 ID, 적절히 설정 필요

    cur.execute('SELECT m.title FROM reviews r JOIN users u ON r.uid = u.id JOIN movies m ON r.mid = m.id WHERE r.uid = %s AND r.mid = %s;',(session['user_id'], movie_id))
    isThereMyReview = cur.fetchall()
    if len(isThereMyReview) > 0:
        cur.execute(
            'update reviews set ratings = %s, review = %s, rev_time = now() where uid = %s and mid = %s',
            (score, content, session['user_id'],movie_id))

    else:
        cur.execute(
            'INSERT INTO reviews (mid, uid, ratings, review, rev_time) VALUES (%s, %s, %s, %s, now())',
            (movie_id, user_id, score, content))


    cur.execute('select title from movies where id = %s', (movie_id))
    title = cur.fetchall()[0][0]
    return redirect(url_for('movie_info', title=title))  # 영화 정보 페이지로 리다이렉트

@app.route('/follow/<user_id>',methods=['POST'])
def follow(user_id):
    my_id = session['user_id']
    following_id = user_id
    cur.execute("select * from ties where id = '{}' and opid = '{}'and tie = '{}'".format(my_id, following_id,'follow'))
    isFollowed = cur.fetchall()
    if len(isFollowed) == 0:
        cur.execute("DELETE FROM ties WHERE id = '{}' AND opid = '{}' AND tie = 'mute';".format(my_id, following_id))
        cur.execute('INSERT INTO ties (id, opid, tie) VALUES (%s, %s, %s);', (my_id, following_id, 'follow'))
    cur.execute(
        "SELECT m.title, m.director, m.genre, COALESCE(CAST(ROUND(AVG(r.ratings), 1) AS VARCHAR), 'None') AS avg_ratings, m.rel_date FROM movies m LEFT JOIN reviews r ON m.id = r.mid GROUP BY m.title, m.director, m.genre, m.rel_date ORDER BY m.rel_date DESC;")
    movies = cur.fetchall()
    cur.execute(
        "SELECT ratings, users.id, title, review, rev_time FROM reviews, users, movies where mid = movies.id and uid = users.id order by rev_time desc;")
    reviews = cur.fetchall()
    return  render_template("main.html", movies=movies, reviews=reviews, user_id=session['user_id'])


@app.route('/mute/<user_id>', methods=['POST'])
def mute(user_id):
    my_id = session['user_id']
    muting_id = user_id
    cur.execute(
        "select * from ties where id = '{}' and opid = '{}'and tie = '{}'".format(my_id, muting_id, 'mute'))
    isMuted = cur.fetchall()
    if len(isMuted) == 0:
        cur.execute("DELETE FROM ties WHERE id = '{}' AND opid = '{}' AND tie = 'follow';".format(my_id, muting_id))
        cur.execute('insert into ties values(%s, %s, %s);',(my_id, muting_id,'mute'))
    cur.execute(
        "SELECT m.title, m.director, m.genre, COALESCE(CAST(ROUND(AVG(r.ratings), 1) AS VARCHAR), 'None') AS avg_ratings, m.rel_date FROM movies m LEFT JOIN reviews r ON m.id = r.mid GROUP BY m.title, m.director, m.genre, m.rel_date ORDER BY m.rel_date DESC;")
    movies = cur.fetchall()
    cur.execute(
        "SELECT ratings, users.id, title, review, rev_time FROM reviews, users, movies where mid = movies.id and uid = users.id order by rev_time desc;")
    reviews = cur.fetchall()
    return render_template("main.html", movies=movies, reviews=reviews, user_id=session['user_id'])

@app.route('/unfollow/<user_id>',methods=['POST'])
def unfollow(user_id):
    my_id = session['user_id']
    following_id = user_id

    cur.execute("DELETE FROM ties WHERE id = '{}' AND opid = '{}' AND tie = 'follow';".format(my_id, following_id))
    cur.execute(
        "SELECT m.title, m.director, m.genre, COALESCE(CAST(ROUND(AVG(r.ratings), 1) AS VARCHAR), 'None') AS avg_ratings, m.rel_date FROM movies m LEFT JOIN reviews r ON m.id = r.mid GROUP BY m.title, m.director, m.genre, m.rel_date ORDER BY m.rel_date DESC;")
    movies = cur.fetchall()
    cur.execute(
        "SELECT ratings, users.id, title, review, rev_time FROM reviews, users, movies where mid = movies.id and uid = users.id order by rev_time desc;")
    reviews = cur.fetchall()
    return render_template("main.html", movies=movies, reviews=reviews, user_id=session['user_id'])


@app.route('/unmute/<user_id>', methods=['POST'])
def unmute(user_id):
    my_id = session['user_id']
    muting_id = user_id

    cur.execute("DELETE FROM ties WHERE id = '{}' AND opid = '{}' AND tie = 'mute';".format(my_id, muting_id))
    cur.execute(
        "SELECT m.title, m.director, m.genre, COALESCE(CAST(ROUND(AVG(r.ratings), 1) AS VARCHAR), 'None') AS avg_ratings, m.rel_date FROM movies m LEFT JOIN reviews r ON m.id = r.mid GROUP BY m.title, m.director, m.genre, m.rel_date ORDER BY m.rel_date DESC;")
    movies = cur.fetchall()
    cur.execute(
        "SELECT ratings, users.id, title, review, rev_time FROM reviews, users, movies where mid = movies.id and uid = users.id order by rev_time desc;")
    reviews = cur.fetchall()
    return render_template("main.html", movies=movies, reviews=reviews, user_id=session['user_id'])

@app.route('/add-movie', methods=['POST'])
def add_movie():
    title = request.form['title']
    director = request.form['director']
    genre = request.form['genre']
    rel_date = request.form['date']

    cur.execute('SELECT MAX(id) FROM movies;')
    max_id = int(cur.fetchall()[0][0])
    cur.execute("INSERT INTO movies (id, title, director, genre, rel_date) VALUES ('{}', '{}', '{}', '{}','{}')".format(str(max_id + 1), title, director, genre, rel_date))

    cur.execute(
        "SELECT m.title, m.director, m.genre, COALESCE(CAST(ROUND(AVG(r.ratings), 1) AS VARCHAR), 'None') AS avg_ratings, m.rel_date FROM movies m LEFT JOIN reviews r ON m.id = r.mid GROUP BY m.title, m.director, m.genre, m.rel_date ORDER BY m.rel_date DESC;")
    movies = cur.fetchall()
    cur.execute(
        "SELECT ratings, users.id, title, review, rev_time FROM reviews, users, movies where mid = movies.id and uid = users.id order by rev_time desc;")
    reviews = cur.fetchall()
    return render_template("main.html", movies=movies, reviews=reviews, user_id=session['user_id'])

@app.route('/leader-board', methods = ['get'])
def show_leader_board():
    cur.execute("SELECT r.uid, COUNT(*) AS review_count FROM reviews r GROUP BY r.uid ORDER BY review_count DESC LIMIT 5;")
    users = cur.fetchall()
    return render_template("leaderboard.html", login_id = session['user_id'],users= users)
@app.route('/recommendation', methods = ['get'])
def movie_recommendation():
    user_id = session['user_id']
    cur.execute(
        "SELECT m2.title, round(AVG(r2.ratings),1) AS Average_Rating, m2.director, m2.genre, m2.rel_date FROM movies m1 JOIN reviews r ON m1.id = r.mid JOIN movies m2 ON m1.genre = m2.genre JOIN reviews r2 ON m2.id = r2.mid WHERE r.uid = '{}' AND r.ratings >= 4.5 GROUP BY m2.id, m2.title, m2.genre;".format(
            user_id))
    recommended_movies = cur.fetchall()
    return render_template("recommendation.html", login_id = session['user_id'],recommended_movies=recommended_movies)

if __name__ == '__main__':
    app.run(debug=True)
