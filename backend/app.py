from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, backref
import os
from werkzeug.utils import secure_filename
from collections import Counter
from sqlalchemy import func
import cloudinary
import cloudinary.uploader


app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)


# ---- アップロード設定 ----
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---- DB設定 ----
# Render の環境変数から DATABASE_URL を読み込む
db_url = os.environ.get("DATABASE_URL", "sqlite:///mawari.db")
# Render の PostgreSQL URL が "postgres://" の場合があるので変換
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

DATABASE_URL = db_url

engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# ---- Cloudinary 設定 ----
cloudinary.config(
    cloudinary_url=os.environ.get("CLOUDINARY_URL")
)



# ---- モデル定義 ----
class Person(Base):
    __tablename__ = "people"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    birth = Column(String)
    blood_type = Column(String)
    mbti = Column(String)
    love_type = Column(String)
    phrase = Column(String)
    image_path = Column(String)

    # 🔹多対多のリレーション定義
    tags = relationship(
        "GroupTag",
        secondary="person_tags",
        back_populates="people"
    )


class GroupTag(Base):
    __tablename__ = "group_tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    people = relationship(
        "Person",
        secondary="person_tags",
        back_populates="tags"
    )


class PersonTag(Base):
    __tablename__ = "person_tags"
    id = Column(Integer, primary_key=True)
    # 🔹ForeignKey を追加
    person_id = Column(Integer, ForeignKey("people.id"))
    tag_id = Column(Integer, ForeignKey("group_tags.id"))

Base.metadata.create_all(engine)


# ---- 表示用辞書 ----
MBTI_LABELS = {
    "INTJ": "INTJ（建築家）", "INTP": "INTP（論理学者）", "ENTJ": "ENTJ（指揮官）", "ENTP": "ENTP（討論者）",
    "INFJ": "INFJ（提唱者）", "INFP": "INFP（仲介者）", "ENFJ": "ENFJ（主人公）", "ENFP": "ENFP（活動家）",
    "ISTJ": "ISTJ（管理者）", "ISFJ": "ISFJ（擁護者）", "ESTJ": "ESTJ（幹部）", "ESFJ": "ESFJ（領事館）",
    "ISTP": "ISTP（巨匠）", "ISFP": "ISFP（冒険者）", "ESTP": "ESTP（起業家）", "ESFP": "ESFP（エンターテイナー）",
}

LOVE_LABELS = {
    "LCRO": "LCRO（ボス猫）", "LCRE": "LCRE（隠れベイビー）", "LCPO": "LCPO（主役体質）", "LCPE": "LCPE（ツンデレヤンキー）",
    "LARO": "LARO（憧れの先輩）", "LARE": "LARE（カリスマバランサー）", "LAPO": "LAPO（パーフェクトカメレオン）", "LAPE": "LAPE（キャプテンライオン）",
    "FCRO": "FCRO（ロマンスマジシャン）", "FCRE": "FCRE（ちゃっかりうさぎ）", "FCPO": "FCPO（恋愛モンスター）", "FCPE": "FCPE（忠犬ハチ公）",
    "FARO": "FARO（不思議生命体）", "FARE": "FARE（敏腕マネージャー）", "FAPO": "FAPO（デビル天使）", "FAPE": "FAPE（最後の恋人）",
}


# ============================================
# ページ系ルート
# ============================================

@app.route("/")
def index():
    session = Session()
    people = session.query(Person).all()
    tags = session.query(GroupTag).all()
    session.close()
    return render_template("index.html", title="図鑑", people=people, tags=tags)


@app.route("/register", methods=["GET", "POST"])
def register():
    session = Session()
    tags = session.query(GroupTag).all()

    if request.method == "POST":
        name = request.form["name"]
        birth = request.form.get("birth", "")
        blood_type = request.form.get("blood_type", "")
        mbti = request.form.get("mbti", "")
        love_type = request.form.get("love_type", "")
        phrase = request.form.get("phrase", "")

        image = request.files["image"]
        image_url = None  # ←重要

        if image and allowed_file(image.filename):
            upload_result = cloudinary.uploader.upload(image)
            image_url = upload_result.get("secure_url")

        person = Person(
            name=name,
            birth=birth,
            blood_type=blood_type,
            mbti=mbti,
            love_type=love_type,
            phrase=phrase,
            image_path=image_url,   # ← Cloudinary のURL
        )
        session.add(person)
        session.commit()

        # タグ登録
        selected_tags = request.form.getlist("tags")
        for tag_id in selected_tags:
            session.add(PersonTag(person_id=person.id, tag_id=int(tag_id)))
        session.commit()

        session.close()
        return redirect(url_for("index"))

    session.close()
    return render_template("register.html", title="登録", tags=tags,
                           MBTI_LABELS=MBTI_LABELS, LOVE_LABELS=LOVE_LABELS)




@app.route("/edit/<int:person_id>", methods=["GET", "POST"])
def edit_person(person_id):
    session = Session()
    person = session.query(Person).filter_by(id=person_id).first()

    if not person:
        session.close()
        return "データが見つかりません。<br><a href='/'>戻る</a>"

    all_tags = session.query(GroupTag).all()
    current_tag_ids = [pt.tag_id for pt in session.query(PersonTag).filter_by(person_id=person_id).all()]

    if request.method == "POST":
        # 基本情報の更新
        person.name = request.form["name"]
        person.birth = request.form.get("birth", "")
        person.blood_type = request.form.get("blood_type", "")
        person.mbti = request.form.get("mbti", "")
        person.love_type = request.form.get("love_type", "")
        person.phrase = request.form.get("phrase", "")

        # 新しい画像がアップロードされた場合だけ Cloudinary に再アップロード
        image = request.files["image"]
        if image and allowed_file(image.filename):
            upload_result = cloudinary.uploader.upload(image)
            person.image_path = upload_result.get("secure_url")

        # タグ更新（全部削除して追加し直す）
        session.query(PersonTag).filter_by(person_id=person_id).delete()
        selected_tag_ids = [int(tid) for tid in request.form.getlist("tags")]
        for tag_id in selected_tag_ids:
            session.add(PersonTag(person_id=person_id, tag_id=tag_id))

        session.commit()
        session.close()
        return redirect(url_for("index"))

    # 表示用データ
    person_dict = {
        "id": person.id,
        "name": person.name,
        "birth": person.birth,
        "blood_type": person.blood_type,
        "mbti": person.mbti,
        "love_type": person.love_type,
        "phrase": person.phrase,
        "image_path": person.image_path,
    }

    session.close()
    return render_template(
        "edit.html",
        person=person_dict,
        tags=all_tags,
        selected_tags=current_tag_ids,
        MBTI_LABELS=MBTI_LABELS,
        LOVE_LABELS=LOVE_LABELS
    )




@app.route("/delete/<int:person_id>")
def delete_person(person_id):
    session = Session()
    person = session.query(Person).filter_by(id=person_id).first()

    if person:
        # Cloudinary の画像削除
        if person.image_path:
            try:
                # Cloudinary URL 例：
                # https://res.cloudinary.com/.../upload/v1234567/xxxx/yyyy.png

                url = person.image_path

                # 1. cloudinary の "upload/" より後ろを取得
                #    例 → v12345/xxx/yyy.png
                part = url.split("/upload/")[-1]

                # 2. 拡張子を除去（.png など）
                part = part.rsplit(".", 1)[0]

                # 3. public_id = part 全体
                public_id = part

                # Cloudinary 削除
                cloudinary.uploader.destroy(public_id)

            except Exception as e:
                print("Cloudinary delete error:", e)

        # DBから人物削除
        session.delete(person)
        session.commit()

    session.close()
    return redirect(url_for("index"))



@app.route("/settings", methods=["GET", "POST"])
def settings():
    session = Session()
    if request.method == "POST":
        new_tag = request.form.get("tag_name")
        if new_tag and not session.query(GroupTag).filter_by(name=new_tag).first():
            session.add(GroupTag(name=new_tag))
            session.commit()

    delete_id = request.args.get("delete")
    if delete_id:
        tag = session.query(GroupTag).filter_by(id=delete_id).first()
        if tag:
            session.delete(tag)
            session.commit()

    tags = session.query(GroupTag).all()
    session.close()
    return render_template("settings.html", tags=tags)



@app.route("/compatibility")
def compatibility_page():
    """相性診断ページ表示用（GET）"""
    return render_template("compatibility.html", title="相性診断")


# ============================================
# API系ルート
# ============================================

@app.route("/person/<int:person_id>")
def get_person(person_id):
    session = Session()
    person = session.query(Person).filter_by(id=person_id).first()
    if not person:
        session.close()
        return jsonify({"error": "not found"}), 404

    tag_links = session.query(PersonTag).filter_by(person_id=person_id).all()
    tag_ids = [t.tag_id for t in tag_links]
    tags = session.query(GroupTag).filter(GroupTag.id.in_(tag_ids)).all()
    tag_names = [t.name for t in tags]
    session.close()

    return jsonify({
        "id": person.id,
        "name": person.name,
        "birth": person.birth,
        "blood_type": person.blood_type,
        "mbti": person.mbti,
        "love_type": person.love_type,
        "phrase": person.phrase,
        "image_path": person.image_path,
        "tags": tag_names
    })


@app.route("/filter", methods=["POST"])
def filter_people():
    data = request.get_json()
    name = data.get("name", "").strip()
    blood_type = data.get("blood_type", "")
    mbti = data.get("mbti", "")
    love_type = data.get("love_type", "")
    tags = data.get("tags", [])

    session = Session()
    query = session.query(Person)

    if name:
        query = query.filter(Person.name.contains(name))
    if blood_type:
        query = query.filter(Person.blood_type == blood_type)
    if mbti:
        query = query.filter(Person.mbti == mbti)
    if love_type:
        query = query.filter(Person.love_type == love_type)

    results = query.all()

    if tags:
        filtered = []
        for person in results:
            pt = session.query(PersonTag).filter_by(person_id=person.id).all()
            person_tag_ids = [p.tag_id for p in pt]
            if any(tag_id in person_tag_ids for tag_id in tags):
                filtered.append(person)
        results = filtered

    response = []
    for p in results:
        tag_links = session.query(PersonTag).filter_by(person_id=p.id).all()
        tag_ids = [t.tag_id for t in tag_links]
        tag_names = [t.name for t in session.query(GroupTag).filter(GroupTag.id.in_(tag_ids)).all()]
        response.append({
            "id": p.id,
            "name": p.name,
            "image_path": p.image_path,
            "birth": p.birth,
            "blood_type": p.blood_type,
            "mbti": p.mbti,
            "love_type": p.love_type,
            "phrase": p.phrase,
            "tags": tag_names
        })

    session.close()
    return jsonify(response)


@app.route("/sort", methods=["POST"])
def sort_people():
    data = request.get_json()
    key = data.get("key")

    session = Session()
    people = session.query(Person).all()

    # ==== ソートロジック ====
    if key == "name":
        people.sort(key=lambda p: p.name or "")
    elif key == "mbti":
        people.sort(key=lambda p: p.mbti or "")
    elif key == "love_type":
        people.sort(key=lambda p: p.love_type or "")
    elif key == "blood_type":
        people.sort(key=lambda p: p.blood_type or "")
    elif key == "tag":
        # 人物が持つ最初のタグ名でソート
        def first_tag_name(person):
            return person.tags[0].name if person.tags else ""
        people.sort(key=first_tag_name)

    # JSON 返す
    result = []
    for p in people:
        result.append({
            "id": p.id,
            "name": p.name,
            "image_path": p.image_path
        })

    session.close()
    return jsonify(result)


@app.route("/stats")
def stats():
    session = Session()

    # 全員
    people = session.query(Person).all()

    # 各分布（空文字やNoneは除外）
    mbti_counts = Counter([p.mbti for p in people if getattr(p, "mbti", None)])
    love_counts = Counter([p.love_type for p in people if getattr(p, "love_type", None)])
    blood_counts = Counter([p.blood_type for p in people if getattr(p, "blood_type", None)])

    # グループタグ分布（JOINで集計：リレーション未定義でもOK）
    tag_rows = (
        session.query(GroupTag.name, func.count(PersonTag.id))
        .join(PersonTag, GroupTag.id == PersonTag.tag_id)
        .group_by(GroupTag.id, GroupTag.name)
        .all()
    )
    tag_counts = {name: cnt for name, cnt in tag_rows}

    session.close()

    return render_template(
        "stats.html",
        mbti_counts=dict(mbti_counts),
        love_counts=dict(love_counts),
        blood_counts=dict(blood_counts),
        tag_counts=dict(tag_counts),
    )


@app.route("/stats_members")
def stats_members():
    category = request.args.get("type")
    value = request.args.get("value")

    session = Session()
    query = session.query(Person)

    if category == "mbti":
        people = query.filter_by(mbti=value).all()
    elif category == "love":
        people = query.filter_by(love_type=value).all()
    elif category == "blood":
        people = query.filter_by(blood_type=value).all()
    elif category == "tag":
        people = query.join(Person.tags).filter(GroupTag.name == value).all()
    else:
        people = []

    session.close()
    return jsonify([{"id": p.id, "name": p.name} for p in people])






# ============================================
# 💞 相性診断API
# ============================================
@app.route("/compatibility_api", methods=["POST"])
def compatibility_api():
    data = request.get_json()
    id1 = data.get("id1")
    id2 = data.get("id2")

    session = Session()
    p1 = session.query(Person).filter_by(id=id1).first()
    p2 = session.query(Person).filter_by(id=id2).first()

    result = calculate_compatibility(p1, p2) if p1 and p2 else None
    session.close()

    if not result:
        return jsonify({"error": "Invalid person IDs"})

    return jsonify(result)




def calculate_compatibility(p1, p2):
    """MBTI・血液型の相性スコア＆コメントをまとめて返す"""

    result = {
        "p1": p1.name,
        "p2": p2.name
    }

    # ================================
    # 🔷 MBTIランキング
    # ================================
    mbti_rankings = {
        "INTJ": ["ESFJ","ISFP","ENTP","INFJ","ENFJ","ESTJ","INTJ","INTP","INFP","ISTP","ISFJ","ISTJ","ESTP","ENFP","ENTJ","ESFP"],
        "INTP": ["ESFP","ISFJ","ENTJ","ISTP","ESTP","ENFP","INTP","INTJ","ISTJ","INFJ","ISFP","INFP","ENFJ","ESTJ","ENTP","ESFJ"],
        "ENTJ": ["ISFJ","ESFP","INTP","ENFJ","INFJ","ISTJ","ENTJ","ENTP","ESTP","ENFP","ESFJ","ESTJ","ISTP","INFP","INTJ","ISFP"],
        "ENTP": ["ISFP","ESFJ","INTJ","ESTP","ISTP","INFP","ENTP","ENTJ","ENFJ","ESTJ","ESFP","ENFP","INFJ","ISTJ","INTP","ISFJ"],
        "INFJ": ["ESTJ","ISTP","ENFP","INTJ","ENTJ","ESFJ","INFJ","INFP","INTP","ISFP","ISTJ","ISFJ","ESFP","ENTP","ENFJ","ESTP"],
        "ENFJ": ["ISTJ","ESTP","INFP","ENTJ","INTJ","ISFJ","ENFJ","ENFP","ESFP","ENTP","ESTJ","ESFJ","ISFP","INTP","INFJ","ISTP"],
        "INFP": ["ESTP","ISTJ","ENFJ","ISFP","ESFP","ENTP","INFP","INFJ","ISFJ","INTJ","ISTP","INTP","ENTJ","ESFJ","ENFP","ESTJ"],
        "ENFP": ["ISTP","ESTJ","INFJ","ESFP","ISFP","INTP","ENFP","ENFJ","ENTJ","ESFJ","ESTP","ENTP","INTJ","ISFJ","INFP","ISTJ"],
        "ISTJ": ["ENFJ","INFP","ESTP","ISFJ","ESFJ","ENTJ","ISTJ","ISTP","ISFP","INTP","INFJ","INTJ","ENTP","ESFP","ESTJ","ENFP"],
        "ISFJ": ["ENTJ","INTP","ESFP","ISTJ","ESTJ","ENFJ","ISFJ","ISFP","ISTP","INFP","INTJ","INFJ","ENFP","ESTP","ESFJ","ENTP"],
        "ESTJ": ["INFJ","ENFP","ISTP","ESFJ","ISFJ","INTJ","ESTJ","ESTP","ENTP","ESFP","ENFJ","ENTJ","INTP","ISFP","ISTJ","INFP"],
        "ESFJ": ["INTJ","ENTP","ISFP","ESTJ","ISTJ","INFJ","ESFJ","ESFP","ENFP","ESTP","ENTJ","ENFJ","INFP","ISTP","ISFJ","INTP"],
        "ESTP": ["INFP","ENFJ","ISTJ","ENTP","INTP","ISFP","ESTP","ESTJ","ESFJ","ENTJ","ENFP","ESFP","ISFJ","INTJ","ISTP","INFJ"],
        "ISTP": ["ENFP","INFJ","ESTJ","INTP","ENTP","ESFP","ISTP","ISTJ","INTJ","ISFJ","INFP","ISFP","ESFJ","ENTJ","ESTP","ENFJ"],
        "ISFP": ["ENTP","INTJ","ESFJ","INFP","ENFP","ESTP","ISFP","ISFJ","INFJ","ISTJ","INTP","ISTP","ESTJ","ENFJ","ESFP","ENTJ"],
        "ESFP": ["INTP","ENTJ","ISFJ","ENFP","INFP","ISTP","ESFP","ESFJ","ESTJ","ENFJ","ENTP","ESTP","ISTJ","INFJ","ISFP","INTJ"]
    }

    # ================================
    # 🔷 MBTIコメント
    # ================================
    rank_comments = {
        1:"💘 運命レベルの相性！自然に惹かれ合う最強ペア。",
        2:"💗 とても相性が良く、お互いを深く理解し合える関係。",
        3:"✨ 相性は高め。尊敬し合える素敵なコンビ。",
        4:"😊 仲良くなりやすく、成長し合える心地よい関係。",
        5:"😀 気が合うことが多い、安心できる相性。",
        6:"🙂 相性は良い方。自然体でいられる組み合わせ。",
        7:"😌 普通の相性。お互いの距離感を保てば快適。",
        8:"😐 可もなく不可もなく。理解し合うには工夫が必要。",
        9:"😅 少し価値観のズレがあるけど、乗り越えられる範囲。",
        10:"⚖️ 合う部分もあるが調整が必要。",
        11:"🌀 やや波がありやすい相性。歩み寄りが大事。",
        12:"💦 理解し合うには時間がかかる可能性あり。",
        13:"🔥 衝突しやすい組み合わせ。でも刺激は多い。",
        14:"⚠️ 価値観が大きく異なりやすい。理解が鍵。",
        15:"💣 相性は低め。工夫しないとすれ違いやすい。",
        16:"🧊 最低レベルの相性。努力しないと距離が縮みにくい。"
    }

    # ================================
    # 🔷 血液型ランキング（性別なし）
    # ================================
    blood_rankings = {
        "A":  ["O", "A", "AB", "B"],
        "B":  ["O", "B", "AB", "A"],
        "O":  ["A", "O", "B", "AB"],
        "AB": ["B", "A", "O", "AB"]
    }

    blood_score_table = [95, 80, 60, 40]  # 上位ほどスコア高い

    # ================================
    # ⭐ MBTIスコア計算
    # ================================
    mbti1, mbti2 = p1.mbti, p2.mbti

    if mbti1 in mbti_rankings:
        rank = mbti_rankings[mbti1].index(mbti2) + 1
    else:
        rank = None

    mbti_score = 100 - (rank - 1) * 5 if rank else None
    mbti_comment = rank_comments.get(rank, "相性データがありません。")

    result["mbti1"] = mbti1
    result["mbti2"] = mbti2
    result["mbti_rank"] = rank
    result["mbti_score"] = mbti_score
    result["mbti_comment"] = mbti_comment

    # ================================
    # ⭐ 血液型スコア計算
    # ================================
    b1, b2 = p1.blood_type, p2.blood_type

    if b1 and b2 and b1 in blood_rankings:
        b_index = blood_rankings[b1].index(b2)
        blood_score = blood_score_table[b_index]
    else:
        blood_score = None

    result["blood1"] = b1
    result["blood2"] = b2
    result["blood_score"] = blood_score
    result["blood_rank"] = b_index + 1 if b1 and b2 else None

    return result






# ============================================
# メイン
# ============================================

if __name__ == "__main__":
    app.run(debug=True)




# ============================================
# これからの発展性
"今は、自分で人物を登録して増やしていく感じのアプリやけど、アカウント登録機能ができたら、フレンド交換した相手が図鑑に登録されていく形でも面白いかなと思った。"
"各人物の登録時や編集時に、「家族」グループや「友達」グループ、「恋人」相手などを選択できるようになったら、相関図を作る時とかに面白そう。"
"もっとシニカル（皮肉のある）なアプリにしてもいいかも。でもどうやって？アイデアがない。"
# ============================================