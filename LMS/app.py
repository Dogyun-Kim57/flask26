# pip install flask
# 플라스크란?
# 파이썬으로 만든 db연동 콘솔 프로그램을 웹으로 연결하는 프레임워크임
# 프레임워크 : 미리 만들어 놓은 틀 안에서 작업하는 공간
# app.py 는 플라스크로 서버를 동작하기 위한 파일명(기본파일)
# static, templates 폴더 필수 (프론트용 파일 모이는 곳)
# static : css, js, 이미지 (정적 리소스)
# templates : html (동적 렌더링 템플릿)

from flask import Flask, render_template, request, redirect, url_for, session

from LMS.common import Session
from LMS.domain import Board
from LMS.domain import Score

#                플라스크   프론트연결     요청,응답   주소전달    주소생성   상태저장소

app = Flask(__name__)
app.secret_key = 'aasdvvs'
# 세션을 사용하기 위해 보안키 설정 (아무 문자열이나 입력)

@app.route('/login', methods=['GET','POST'])  # http://localhost:5000/login
def login():
    if request.method == 'GET':
        return render_template('login.html')

    uid = request.form.get('uid')
    upw = request.form.get('upw')

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT id, name, uid, role
                FROM members
                WHERE uid = %s AND password = %s
            """
            cursor.execute(sql, (uid, upw))
            user = cursor.fetchone()

            if user:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_uid'] = user['uid']
                session['user_role'] = user['role']
                return redirect(url_for('index'))
            else:
                return "<script>alert('아이디나 비번이 틀렸습니다.');history.back();</script>"
    finally:
        conn.close()


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/join', methods=['GET','POST'])
def join():
    if request.method == 'GET':
        return render_template('join.html')

    uid = request.form.get('uid')
    password = request.form.get('password')
    name = request.form.get('name')

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM members WHERE uid = %s", (uid,))
            if cursor.fetchone():
                return "<script>alert('이미 존재하는 아이디입니다.'); history.back();</script>"

            sql = "INSERT INTO members (uid, password, name) VALUES (%s, %s, %s)"
            cursor.execute(sql, (uid, password, name))
            conn.commit()

            return "<script>alert('회원가입이 완료되었습니다!'); location.href='/login';</script>"
    except Exception as e:
        print(f"회원가입 에러: {e}")
        return "가입 중 오류가 발생했습니다.\njoin()메서드를 확인하세요!!!"
    finally:
        conn.close()


@app.route('/member/edit', methods=['GET', 'POST'])
def member_edit():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT * FROM members WHERE id = %s", (session['user_id'],))
                user_info = cursor.fetchone()
                return render_template('member_edit.html', user=user_info)

            new_name = request.form.get('name')
            new_pw = request.form.get('password')

            if new_pw:
                sql = "UPDATE members SET name = %s, password = %s WHERE id = %s"
                cursor.execute(sql, (new_name, new_pw, session['user_id']))
            else:
                sql = "UPDATE members SET name = %s WHERE id = %s"
                cursor.execute(sql, (new_name, session['user_id']))

            conn.commit()
            session['user_name'] = new_name
            return "<script>alert('정보가 수정되었습니다.'); location.href='/mypage';</script>"
    except Exception as e:
        print(f"회원수정 에러: {e}")
        return "수정 중 오류가 발생했습니다.\nmember_edit()메서드를 확인하세요!!!"
    finally:
        conn.close()


@app.route('/mypage')
def mypage():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM members WHERE id = %s", (session['user_id'],))
            user_info = cursor.fetchone()

            cursor.execute(
                "SELECT COUNT(*) as board_count FROM boards WHERE member_id = %s",
                (session['user_id'],)
            )
            board_count = cursor.fetchone()['board_count']

            return render_template('mypage.html', user=user_info, board_count=board_count)
    finally:
        conn.close()


#################################### 게시판 CRUD ####################################

@app.route('/board/write', methods=['GET', 'POST'])
def board_write():
    if request.method == 'GET':
        if 'user_id' not in session:
            return '<script>alert("로그인 후 이용 가능합니다."); location.href="/login";</script>'
        return render_template('board_write.html')

    title = request.form.get('title')
    content = request.form.get('content')
    member_id = session.get('user_id')

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO boards (member_id, title, content) VALUES (%s, %s, %s)"
            cursor.execute(sql, (member_id, title, content))
            conn.commit()
        return redirect(url_for('board_list'))
    except Exception as e:
        print(f"글쓰기 에러: {e}")
        return "저장 중 에러가 발생했습니다."
    finally:
        conn.close()


@app.route('/board')
def board_list():
    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT b.*, m.name as writer_name
                FROM boards b
                JOIN members m ON b.member_id = m.id
                ORDER BY b.id DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            boards = [Board.from_db(row) for row in rows]
            return render_template('board_list.html', boards=boards)
    finally:
        conn.close()


@app.route('/board/view/<int:board_id>')
def board_view(board_id):
    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT b.*, m.name as writer_name, m.uid as writer_uid
                FROM boards b
                JOIN members m ON b.member_id = m.id
                WHERE b.id = %s
            """
            cursor.execute(sql, (board_id,))
            row = cursor.fetchone()

            if not row:
                return "<script>alert('존재하지 않는 게시글입니다.'); history.back();</script>"

            board = Board.from_db(row)
            return render_template('board_view.html', board=board)
    finally:
        conn.close()


@app.route('/board/edit/<int:board_id>', methods=['GET', 'POST'])
def board_edit(board_id):
    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT * FROM boards WHERE id = %s", (board_id,))
                row = cursor.fetchone()

                if not row:
                    return "<script>alert('존재하지 않는 게시글입니다.'); history.back();</script>"

                if row['member_id'] != session.get('user_id'):
                    return "<script>alert('수정 권한이 없습니다.'); history.back();</script>"

                board = Board.from_db(row)
                return render_template('board_edit.html', board=board)

            title = request.form.get('title')
            content = request.form.get('content')

            sql = "UPDATE boards SET title=%s, content=%s WHERE id=%s"
            cursor.execute(sql, (title, content, board_id))
            conn.commit()

            return redirect(url_for('board_view', board_id=board_id))
    finally:
        conn.close()


@app.route('/board/delete/<int:board_id>')
def board_delete(board_id):
    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "DELETE FROM boards WHERE id = %s"
            cursor.execute(sql, (board_id,))
            conn.commit()

            if cursor.rowcount == 0:
                return "<script>alert('삭제할 게시글이 없거나 권한이 없습니다.'); history.back();</script>"

        return redirect(url_for('board_list'))
    except Exception as e:
        print(f"삭제 에러: {e}")
        return "삭제 중 오류가 발생했습니다."
    finally:
        conn.close()


#################################### 성적 CRUD ####################################

@app.route('/score/add')
def score_add():
    if session.get('user_role') not in ('admin', 'manager'):
        return "<script>alert('권한이 없습니다.'); history.back();</script>"

    target_uid = request.args.get('uid')
    target_name = request.args.get('name')

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM members WHERE uid = %s", (target_uid,))
            student = cursor.fetchone()

            existing_score = None
            if student:
                cursor.execute("SELECT * FROM scores WHERE member_id = %s", (student['id'],))
                row = cursor.fetchone()
                if row:
                    existing_score = Score.from_db(row)

            return render_template(
                'score_form.html',
                target_uid=target_uid,
                target_name=target_name,
                score=existing_score
            )
    finally:
        conn.close()


@app.route('/score/save', methods=['POST'])
def score_save():
    if session.get('user_role') not in ('admin', 'manager'):
        return "권한 오류", 403

    target_uid = request.form.get('target_uid')
    kor = int(request.form.get('korean', 0))
    eng = int(request.form.get('english', 0))
    math = int(request.form.get('math', 0))

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM members WHERE uid = %s", (target_uid,))
            student = cursor.fetchone()

            if not student:
                return "<script>alert('존재하지 않는 학생입니다.'); history.back();</script>"

            temp_score = Score(member_id=student['id'], kor=kor, eng=eng, math=math)

            cursor.execute("SELECT id FROM scores WHERE member_id = %s", (student['id'],))
            is_exist = cursor.fetchone()

            if is_exist:
                sql = """
                    UPDATE scores
                    SET korean=%s, english=%s, math=%s,
                        total=%s, average=%s, grade=%s
                    WHERE member_id=%s
                """
                cursor.execute(
                    sql,
                    (temp_score.kor, temp_score.eng, temp_score.math,
                     temp_score.total, temp_score.avg, temp_score.grade,
                     student['id'])
                )
            else:
                sql = """
                    INSERT INTO scores
                    (member_id, korean, english, math, total, average, grade)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    sql,
                    (student['id'], temp_score.kor, temp_score.eng,
                     temp_score.math, temp_score.total,
                     temp_score.avg, temp_score.grade)
                )

            conn.commit()
            return f"<script>alert('{target_uid} 학생 성적 저장 완료!'); location.href='/score/list';</script>"
    finally:
        conn.close()

@app.route('/score/list')
def score_list():
    # 1. 권한 체크 (관리자나 매니저만 볼 수 있게 설정)
    if session.get('user_role') not in ('admin', 'manager'):
        return "<script>alert('권한이 없습니다.'); history.back();</script>"

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            # 2. JOIN을 사용하여 학생 이름(name)과 성적 데이터를 함께 조회
            # 성적이 없는 학생은 제외하고, 성적이 있는 학생들만 총점 순으로 정렬
            sql = """
                SELECT m.name, m.uid, s.* FROM scores s
                JOIN members m ON s.member_id = m.id
                ORDER BY s.total DESC
            """
            cursor.execute(sql)
            datas = cursor.fetchall()

            # 3. DB에서 가져온 딕셔너리 리스트를 Score 객체 리스트로 변환
            score_objects = []
            for data in datas:
                # Score 클래스에 정의하신 from_db 활용
                s = Score.from_db(data)
                # 객체에 없는 이름(name) 정보는 수동으로 살짝 넣어주기
                s.name = data['name']
                s.uid = data['uid']
                score_objects.append(s)

            return render_template('score_list.html', scores=score_objects)
    finally:
        conn.close()

@app.route('/score/members')
def score_members():
    if session.get('user_role') not in ('admin', 'manager'):
        return "<scrpit>alret('권한이 없습니다.'); history.back();</scrpit>"
    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            # LEFT JOIN을 통해 성적이 있으면 s.id가 숫자로, 없으면 NULL로 나옵니다.
            sql = """
                SELECT m.id, m.uid, m.name, s.id AS score_id
                FROM members m
                LEFT JOIN scores s ON m.id = s.member_id
                WHERE m.role = 'user'
                ORDER BY m.name ASC
            """
            cursor.execute(sql)
            members = cursor.fetchall()
            return render_template('score_member_list.html', members=members)
    finally:
        conn.close()

@app.route('/score/my') # http://localhost:5000/score/my -> get
def score_my():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            # 내 ID로만 조회
            sql = "SELECT * FROM scores WHERE member_id = %s"
            cursor.execute(sql, (session['user_id'],))
            row = cursor.fetchone()
            print(row) # dict 타입으로 결과물 들어옴
            # Score 객체로 변환 (from_db 활용)
            score = Score.from_db(row) if row else None

            return render_template('score_my.html', score=score)

    finally:
        conn.close()





#################################### 성적 CRUD END ####################################




@app.route('/')
def index():
    return render_template('main.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)