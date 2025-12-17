from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, func, event
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
    relationship,
    joinedload,
)
from collections import Counter
import os

from werkzeug.utils import secure_filename  #今後使う可能性もあるので残しておく
import cloudinary
import cloudinary.uploader


#============================================
#Flask アプリ初期化
#============================================
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

#============================================
#環境判定（本番 or ローカル）
#============================================
IS_PRODUCTION = os.environ.get("RENDER") == "true"


#---- アップロード設定（ローカル用のフォルダ：Cloudinary 併用でも一応残す）----
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename: str) -> bool:
    """許可した拡張子かどうかを判定"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


#============================================
#DB 設定
#============================================
#Render の環境変数から DATABASE_URL を読み込む（未設定なら SQLite にフォールバック）
db_url = os.environ.get("DATABASE_URL", "sqlite:///mawari.db")

#Render の PostgreSQL URL が "postgres://" の場合があるので変換
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

DATABASE_URL = db_url

engine = create_engine(DATABASE_URL, echo=not IS_PRODUCTION)
Session = sessionmaker(bind=engine)
Base = declarative_base()


#============================================
#Cloudinary 設定（本番のみ）
#============================================
if IS_PRODUCTION:
    cloudinary.config(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key=os.environ.get("CLOUDINARY_API_KEY"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET")
    )



#============================================
#モデル定義
#============================================
class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    reading = Column(String)
    birth = Column(String)
    blood_type = Column(String)
    mbti = Column(String)
    love_type = Column(String)
    phrase = Column(String)
    image_path = Column(String)

    #多対多のリレーション定義
    tags = relationship(
        "GroupTag",
        secondary="person_tags",
        back_populates="people",
        overlaps="person_tags,tag_links",
    )
    person_tags = relationship(
        "PersonTag",
        back_populates="person",
        overlaps="tags,people",
    )


class GroupTag(Base):
    __tablename__ = "group_tags"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    people = relationship(
        "Person",
        secondary="person_tags",
        back_populates="tags",
        overlaps="person_tags,tag_links",
    )
    tag_links = relationship(
        "PersonTag",
        back_populates="tag",
        overlaps="people,tags",
    )


class PersonTag(Base):
    __tablename__ = "person_tags"

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"))
    tag_id = Column(Integer, ForeignKey("group_tags.id", ondelete="CASCADE"))

    person = relationship(
        "Person",
        back_populates="person_tags",
        overlaps="people,tags",
    )
    tag = relationship(
        "GroupTag",
        back_populates="tag_links",
        overlaps="people,tags",
    )




class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"))
    target_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"))
    relation_type = Column(String)
    strength = Column(Integer)

    source = relationship("Person", foreign_keys=[source_id], backref="relations_from")
    target = relationship("Person", foreign_keys=[target_id], backref="relations_to")






#テーブル作成
Base.metadata.create_all(engine)


#============================================
#表示用辞書（MBTI / ラブタイプ）
#============================================
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

RELATION_TYPES = [
    ("friend", "友達"),
    ("lover", "恋人"),
    ("family", "家族"),
    ("senpai_kohai", "先輩・後輩"),
]
RELATION_TYPE_LABELS = dict(RELATION_TYPES)
#既存データの古い種別ラベル互換
RELATION_TYPE_LABELS.update({
    "senpai": "先輩・後輩",
    "kohai": "先輩・後輩",
})



#============================================
#ヘルパー関数
#============================================

#============================================================
#画像アップロード（Cloudinary or ローカル自動切り替え）
#============================================================
def upload_image(file_storage):
    """本番は Cloudinary、ローカルは /static/uploads に保存"""

    if not file_storage:
        return None

    #-----------------------
    #本番（Render）→ Cloudinary
    #-----------------------
    if IS_PRODUCTION:
        try:
            result = cloudinary.uploader.upload(file_storage)
            return result["secure_url"]
        except Exception as e:
            print("[Cloudinary ERROR]", e)
            #必要なら fallback を入れてもいい（ローカル保存など）
            return None

    #-----------------------
    #ローカル環境 → static/uploads へ保存
    #-----------------------
    filename = secure_filename(file_storage.filename)
    save_dir = "static/uploads"
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, filename)
    file_storage.save(save_path)

    return f"/static/uploads/{filename}"

def delete_cloudinary_image_by_url(image_url):
    """
    Cloudinary の画像 URL から public_id を抽出して削除する関数。
    本番のときだけ動く。ローカル画像は何もしない。
    """
    if not image_url:
        return

    #ローカル保存の場合は処理不要
    if not IS_PRODUCTION:
        return

    try:
        #URL例:
        #https://res.cloudinary.com/xxx/image/upload/v1234567890/abcdef.png
        public_id = image_url.split("/")[-1].split(".")[0]

        cloudinary.uploader.destroy(public_id)
        print(f"[INFO] Cloudinary image deleted: {public_id}")

    except Exception as e:
        print("[ERROR] Failed to delete Cloudinary image:", e)



def get_tag_names_for_person(session, person_id: int):
    """person_id からタグ名一覧を取得"""
    tag_links = session.query(PersonTag).filter_by(person_id=person_id).all()
    if not tag_links:
        return []

    tag_ids = [t.tag_id for t in tag_links]
    tags = session.query(GroupTag).filter(GroupTag.id.in_(tag_ids)).all()
    return [t.name for t in tags]


def person_to_dict(person, tags=None):
    """Person モデルを API / テンプレート用の dict に変換"""
    if tags is None:
        #タグが eager load されている場合は person.tags を優先
        if hasattr(person, "tags") and person.tags:
            tags = [t.name for t in person.tags]
        else:
            tags = []

    return {
        "id": person.id,
        "name": person.name,
        "reading": person.reading,
        "birth": person.birth,
        "blood_type": person.blood_type,
        "mbti": person.mbti,
        "love_type": person.love_type,
        "phrase": person.phrase,
        "image_path": person.image_path,
        "tags": tags,
    }


#============================================
#ページ系ルート
#============================================

@event.listens_for(engine, "connect")
def enable_sqlite_fk_constraints(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@app.route("/")
def index():
    """トップページ：図鑑表示"""
    session = Session()
    try:
        #Person と tags を一緒に読み込む（N+1 回避）
        people = session.query(Person).options(
            joinedload(Person.tags)
        ).all()

        tags = session.query(GroupTag).all()

        #Person → dict に変換
        people_json = [
            person_to_dict(p, tags=[t.name for t in p.tags])
            for p in people
        ]

        return render_template(
            "index.html",
            title="図鑑",
            people=people_json,
            tags=tags,
            MBTI_LABELS=MBTI_LABELS,
            LOVE_LABELS=LOVE_LABELS,
            active="index"
        )
    finally:
        session.close()


@app.route("/register", methods=["GET", "POST"])
def register():
    """登録画面（GET）＋ 登録処理（POST）"""
    session = Session()
    try:
        tags = session.query(GroupTag).all()

        if request.method == "POST":
            name = request.form["name"]
            reading = request.form.get("reading", "")
            birth = request.form.get("birth", "")
            blood_type = request.form.get("blood_type", "")
            mbti = request.form.get("mbti", "")
            love_type = request.form.get("love_type", "")
            phrase = request.form.get("phrase", "")

            image_file = request.files.get("image")
            image_url = upload_image(image_file)

            person = Person(
                name=name,
                reading=reading,
                birth=birth,
                blood_type=blood_type,
                mbti=mbti,
                love_type=love_type,
                phrase=phrase,
                image_path=image_url,
            )
            session.add(person)
            session.commit()

            #タグ登録
            selected_tags = request.form.getlist("tags")
            for tag_id in selected_tags:
                session.add(PersonTag(person_id=person.id, tag_id=int(tag_id)))
            session.commit()

            return redirect(url_for("index"))

        #GET
        return render_template(
            "register.html",
            title="登録",
            tags=tags,
            MBTI_LABELS=MBTI_LABELS,
            LOVE_LABELS=LOVE_LABELS,
            active="register"
        )
    finally:
        session.close()


@app.route("/edit/<int:person_id>", methods=["GET", "POST"])
def edit_person(person_id):
    """人物編集画面（GET）＋ 更新処理（POST）"""
    session = Session()
    try:
        person = session.query(Person).filter_by(id=person_id).first()
        if not person:
            return "データが見つかりません。<br><a href='/'>戻る</a>"

        all_tags = session.query(GroupTag).all()
        current_tag_ids = [
            pt.tag_id for pt in session.query(PersonTag).filter_by(person_id=person_id).all()
        ]

        if request.method == "POST":
            #基本情報の更新
            person.name = request.form["name"]
            person.reading = request.form.get("reading", "")
            person.birth = request.form.get("birth", "")
            person.blood_type = request.form.get("blood_type", "")
            person.mbti = request.form.get("mbti", "")
            person.love_type = request.form.get("love_type", "")
            person.phrase = request.form.get("phrase", "")

            #新しい画像がアップロードされた場合だけ Cloudinary に再アップロード
            image_file = request.files.get("image")
            new_image_url = upload_image(image_file)
            if new_image_url:
                person.image_path = new_image_url

            #タグ更新（全部削除して追加し直す）
            session.query(PersonTag).filter_by(person_id=person_id).delete()
            selected_tag_ids = [int(tid) for tid in request.form.getlist("tags")]
            for tag_id in selected_tag_ids:
                session.add(PersonTag(person_id=person_id, tag_id=tag_id))

            session.commit()
            return redirect(url_for("index"))

        #GET 表示用データ
        person_dict = person_to_dict(person, tags=None)

        return render_template(
            "edit.html",
            person=person_dict,
            tags=all_tags,
            selected_tags=current_tag_ids,
            MBTI_LABELS=MBTI_LABELS,
            LOVE_LABELS=LOVE_LABELS,
        )
    finally:
        session.close()


@app.route("/delete/<int:person_id>", methods=["POST"])
def delete_person(person_id):
    """人物削除"""
    session = Session()
    try:
        person = session.query(Person).filter_by(id=person_id).first()

        if person:
            #Cloudinary の画像削除（ある場合）
            if person.image_path:
                delete_cloudinary_image_by_url(person.image_path)

            #DB から人物削除（PersonTag 側は外部キー設定に依存、なければ手動削除も検討）
            session.delete(person)
            session.commit()

        return redirect(url_for("index"))
    finally:
        session.close()


@app.route("/settings", methods=["GET", "POST"])
def settings():
    """グループタグ設定ページ"""
    session = Session()
    try:
        #タグ追加（POST）
        if request.method == "POST":
            new_tag = request.form.get("tag_name")
            if new_tag and not session.query(GroupTag).filter_by(name=new_tag).first():
                session.add(GroupTag(name=new_tag))
                session.commit()

        #タグ削除（GET パラメータ delete）
        delete_id = request.args.get("delete")
        if delete_id:
            delete_id_int = int(delete_id)
            tag = session.query(GroupTag).filter_by(id=delete_id_int).first()
            if tag:
                #PersonTag → GroupTag の順に削除
                session.delete(tag)
                session.commit()

        tags = session.query(GroupTag).all()

        return render_template("settings.html", tags=tags, active="settings")
    finally:
        session.close()


@app.route("/compatibility")
def compatibility_page():
    """相性診断ページ表示用（今は index から直接 API を叩いているが、一応残しておく）"""
    return render_template("compatibility.html", title="相性診断")


#============================================
#API 系ルート
#============================================

@app.route("/person/<int:person_id>")
def get_person(person_id):
    """人物詳細（JSON）"""
    session = Session()
    try:
        person = session.query(Person).filter_by(id=person_id).first()
        if not person:
            return jsonify({"error": "not found"}), 404

        tag_names = get_tag_names_for_person(session, person_id)
        return jsonify(person_to_dict(person, tags=tag_names))
    finally:
        session.close()


@app.route("/filter", methods=["POST"])
def filter_people():
    """人物フィルター（JSON 返却）"""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    blood_type = data.get("blood_type", "")
    mbti = data.get("mbti", "")
    love_type = data.get("love_type", "")
    tags = data.get("tags", [])

    session = Session()
    try:
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

        #タグ指定がある場合は Python 側で絞り込み
        if tags:
            tag_ids_filter = set(tags)
            filtered = []
            for person in results:
                person_tag_ids = [
                    pt.tag_id
                    for pt in session.query(PersonTag).filter_by(person_id=person.id).all()
                ]
                if any(tag_id in person_tag_ids for tag_id in tag_ids_filter):
                    filtered.append(person)
            results = filtered

        response = []
        for p in results:
            tag_names = get_tag_names_for_person(session, p.id)
            response.append(person_to_dict(p, tags=tag_names))

        return jsonify(response)
    finally:
        session.close()


@app.route("/stats")
def stats():
    """統計ダッシュボード用ページ"""
    session = Session()
    try:
        people = session.query(Person).all()

        #各分布（空文字や None は除外）
        mbti_counts = Counter(
            [p.mbti for p in people if getattr(p, "mbti", None)]
        )
        love_counts = Counter(
            [p.love_type for p in people if getattr(p, "love_type", None)]
        )
        blood_counts = Counter(
            [p.blood_type for p in people if getattr(p, "blood_type", None)]
        )

        #グループタグ分布（JOIN で集計）
        tag_rows = (
            session.query(GroupTag.name, func.count(PersonTag.id))
            .join(PersonTag, GroupTag.id == PersonTag.tag_id)
            .group_by(GroupTag.id, GroupTag.name)
            .all()
        )
        tag_counts = {name: cnt for name, cnt in tag_rows}

        return render_template(
            "stats.html",
            mbti_counts=dict(mbti_counts),
            love_counts=dict(love_counts),
            blood_counts=dict(blood_counts),
            tag_counts=dict(tag_counts),
            MBTI_LABELS=MBTI_LABELS,
            LOVE_LABELS=LOVE_LABELS,
            active="stats"
        )
    finally:
        session.close()


@app.route("/stats_members")
def stats_members():
    """統計グラフからクリックされたとき、該当メンバーを返す API"""
    category = request.args.get("type")
    value = request.args.get("value")

    session = Session()
    try:
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

        return jsonify([{"id": p.id, "name": p.name} for p in people])
    finally:
        session.close()


#------- ページ表示 -------
@app.route("/relations")
def relations_page():
    session = Session()
    try:
        people = session.query(Person).all()
        relations = session.query(Relationship).all()

        return render_template(
            "relations.html",
            title="関係性",
            people=people,
            relations=relations,
            RELATION_TYPES=RELATION_TYPES,
            RELATION_TYPE_LABELS=RELATION_TYPE_LABELS,
            active="relations"
        )
    finally:
        session.close()


#------- 関係の追加 -------
@app.route("/relations/add", methods=["POST"])
def add_relation():
    session = Session()
    try:
        source_id = int(request.form["source_id"])
        target_id = int(request.form["target_id"])
        relation_type = request.form["relation_type"]
        strength = int(request.form["strength"])

        #同一人物の組み合わせは登録しない
        if source_id == target_id:
            return redirect("/relations")

        #方向なしなので ID の小さい方を source 側に揃えて保存
        normalized_source, normalized_target = sorted([source_id, target_id])

        existing = (
            session.query(Relationship)
            .filter_by(source_id=normalized_source, target_id=normalized_target)
            .first()
        )

        if existing:
            existing.relation_type = relation_type
            existing.strength = strength
        else:
            session.add(
                Relationship(
                    source_id=normalized_source,
                    target_id=normalized_target,
                    relation_type=relation_type,
                    strength=strength,
                )
            )

        session.commit()
        return redirect("/relations")
    finally:
        session.close()


#------- 関係の削除 -------
@app.route("/relations/delete/<int:relation_id>", methods=["POST"])
def delete_relation(relation_id):
    session = Session()
    try:
        r = session.query(Relationship).filter_by(id=relation_id).first()
        if r:
            session.delete(r)
            session.commit()
        return redirect("/relations")
    finally:
        session.close()





#============================================
#💞 相性診断 API
#============================================

@app.route("/compatibility_api", methods=["POST"])
def compatibility_api():
    """2人の ID を受け取り、MBTI / 血液型相性を返す API"""
    data = request.get_json() or {}
    id1 = data.get("id1")
    id2 = data.get("id2")

    session = Session()
    try:
        p1 = session.query(Person).filter_by(id=id1).first()
        p2 = session.query(Person).filter_by(id=id2).first()

        result = calculate_compatibility(p1, p2) if p1 and p2 else None
        if result and p1 and p2:
            result["p1_image"] = p1.image_path
            result["p2_image"] = p2.image_path
    finally:
        session.close()

    if not result:
        return jsonify({"error": "Invalid person IDs"})

    return jsonify(result)


def calculate_compatibility(p1: Person, p2: Person):
    """MBTI・血液型の相性スコア＆コメントをまとめて返す"""

    result = {
        "p1": p1.name,
        "p2": p2.name,
    }

    #================================
    #🔷 MBTI ランキング
    #================================
    mbti_rankings = {
        "INTJ": ["ESFJ", "ISFP", "ENTP", "INFJ", "ENFJ", "ESTJ", "INTJ", "INTP", "INFP", "ISTP", "ISFJ", "ISTJ", "ESTP", "ENFP", "ENTJ", "ESFP"],
        "INTP": ["ESFP", "ISFJ", "ENTJ", "ISTP", "ESTP", "ENFP", "INTP", "INTJ", "ISTJ", "INFJ", "ISFP", "INFP", "ENFJ", "ESTJ", "ENTP", "ESFJ"],
        "ENTJ": ["ISFJ", "ESFP", "INTP", "ENFJ", "INFJ", "ISTJ", "ENTJ", "ENTP", "ESTP", "ENFP", "ESFJ", "ESTJ", "ISTP", "INFP", "INTJ", "ISFP"],
        "ENTP": ["ISFP", "ESFJ", "INTJ", "ESTP", "ISTP", "INFP", "ENTP", "ENTJ", "ENFJ", "ESTJ", "ESFP", "ENFP", "INFJ", "ISTJ", "INTP", "ISFJ"],
        "INFJ": ["ESTJ", "ISTP", "ENFP", "INTJ", "ENTJ", "ESFJ", "INFJ", "INFP", "INTP", "ISFP", "ISTJ", "ISFJ", "ESFP", "ENTP", "ENFJ", "ESTP"],
        "ENFJ": ["ISTJ", "ESTP", "INFP", "ENTJ", "INTJ", "ISFJ", "ENFJ", "ENFP", "ESFP", "ENTP", "ESTJ", "ESFJ", "ISFP", "INTP", "INFJ", "ISTP"],
        "INFP": ["ESTP", "ISTJ", "ENFJ", "ISFP", "ESFP", "ENTP", "INFP", "INFJ", "ISFJ", "INTJ", "ISTP", "INTP", "ENTJ", "ESFJ", "ENFP", "ESTJ"],
        "ENFP": ["ISTP", "ESTJ", "INFJ", "ESFP", "ISFP", "INTP", "ENFP", "ENFJ", "ENTJ", "ESFJ", "ESTP", "ENTP", "INTJ", "ISFJ", "INFP", "ISTJ"],
        "ISTJ": ["ENFJ", "INFP", "ESTP", "ISFJ", "ESFJ", "ENTJ", "ISTJ", "ISTP", "ISFP", "INTP", "INFJ", "INTJ", "ENTP", "ESFP", "ESTJ", "ENFP"],
        "ISFJ": ["ENTJ", "INTP", "ESFP", "ISTJ", "ESTJ", "ENFJ", "ISFJ", "ISFP", "ISTP", "INFP", "INTJ", "INFJ", "ENFP", "ESTP", "ESFJ", "ENTP"],
        "ESTJ": ["INFJ", "ENFP", "ISTP", "ESFJ", "ISFJ", "INTJ", "ESTJ", "ESTP", "ENTP", "ESFP", "ENFJ", "ENTJ", "INTP", "ISFP", "ISTJ", "INFP"],
        "ESFJ": ["INTJ", "ENTP", "ISFP", "ESTJ", "ISTJ", "INFJ", "ESFJ", "ESFP", "ENFP", "ESTP", "ENTJ", "ENFJ", "INFP", "ISTP", "ISFJ", "INTP"],
        "ESTP": ["INFP", "ENFJ", "ISTJ", "ENTP", "INTP", "ISFP", "ESTP", "ESTJ", "ESFJ", "ENTJ", "ENFP", "ESFP", "ISFJ", "INTJ", "ISTP", "INFJ"],
        "ISTP": ["ENFP", "INFJ", "ESTJ", "INTP", "ENTP", "ESFP", "ISTP", "ISTJ", "INTJ", "ISFJ", "INFP", "ISFP", "ESFJ", "ENTJ", "ESTP", "ENFJ"],
        "ISFP": ["ENTP", "INTJ", "ESFJ", "INFP", "ENFP", "ESTP", "ISFP", "ISFJ", "INFJ", "ISTJ", "INTP", "ISTP", "ESTJ", "ENFJ", "ESFP", "ENTJ"],
        "ESFP": ["INTP", "ENTJ", "ISFJ", "ENFP", "INFP", "ISTP", "ESFP", "ESFJ", "ESTJ", "ENFJ", "ENTP", "ESTP", "ISTJ", "INFJ", "ISFP", "INTJ"],
    }

    #================================
    #🔷 MBTI コメント
    #================================
    rank_comments = {
        1: "💘 運命レベルの相性！自然に惹かれ合う最強ペア。",
        2: "💗 とても相性が良く、お互いを深く理解し合える関係。",
        3: "✨ 相性は高め。尊敬し合える素敵なコンビ。",
        4: "😊 仲良くなりやすく、成長し合える心地よい関係。",
        5: "😀 気が合うことが多い、安心できる相性。",
        6: "🙂 相性は良い方。自然体でいられる組み合わせ。",
        7: "😌 普通の相性。お互いの距離感を保てば快適。",
        8: "😐 可もなく不可もなく。理解し合うには工夫が必要。",
        9: "😅 少し価値観のズレがあるけど、乗り越えられる範囲。",
        10: "⚖️ 合う部分もあるが調整が必要。",
        11: "🌀 やや波がありやすい相性。歩み寄りが大事。",
        12: "💦 理解し合うには時間がかかる可能性あり。",
        13: "🔥 衝突しやすい組み合わせ。でも刺激は多い。",
        14: "⚠️ 価値観が大きく異なりやすい。理解が鍵。",
        15: "💣 相性は低め。工夫しないとすれ違いやすい。",
        16: "🧊 最低レベルの相性。努力しないと距離が縮みにくい。",
    }

    #================================
    #🔷 血液型ランキング（性別なし）
    #================================
    blood_rankings = {
        "A": ["O", "A", "AB", "B"],
        "B": ["O", "B", "AB", "A"],
        "O": ["A", "O", "B", "AB"],
        "AB": ["B", "A", "O", "AB"],
    }
    blood_score_table = [95, 80, 60, 40]  #上位ほどスコア高い

    #================================
    #⭐ MBTI スコア計算
    #================================
    mbti1, mbti2 = p1.mbti, p2.mbti
    rank = None

    if mbti1 in mbti_rankings and mbti2 in mbti_rankings[mbti1]:
        rank = mbti_rankings[mbti1].index(mbti2) + 1

    mbti_score = 100 - (rank - 1) * 5 if rank else None
    mbti_comment = rank_comments.get(rank, "相性データがありません。")

    result["mbti1"] = mbti1
    result["mbti2"] = mbti2
    result["mbti_rank"] = rank
    result["mbti_score"] = mbti_score
    result["mbti_comment"] = mbti_comment

    #================================
    #⭐ 血液型スコア計算
    #================================
    b1, b2 = p1.blood_type, p2.blood_type
    blood_score = None
    blood_rank = None

    if b1 and b2 and (b1 in blood_rankings):
        if b2 in blood_rankings[b1]:
            b_index = blood_rankings[b1].index(b2)
            blood_score = blood_score_table[b_index]
            blood_rank = b_index + 1

    result["blood1"] = b1
    result["blood2"] = b2
    result["blood_score"] = blood_score
    result["blood_rank"] = blood_rank

    return result


#============================================================
#関係性を JSON で返すAPI（vis-network用）
#============================================================
@app.route("/api/relations")
def api_relations():
    session = Session()
    try:
        people = session.query(Person).all()
        relations = session.query(Relationship).all()

        people_data = [
            {
                "id": p.id,
                "name": p.name,
                "image": p.image_path
            }
            for p in people
        ]

        relations_data = []
        for r in relations:
            source, target = sorted([r.source_id, r.target_id])
            relations_data.append(
                {
                    "id": r.id,
                    "source": source,
                    "target": target,
                    "type": r.relation_type,
                    "strength": r.strength,
                }
            )

        return jsonify({"people": people_data, "relations": relations_data})
    finally:
        session.close()



#============================================
#メイン
#============================================
if __name__ == "__main__":
    app.run(debug=True)


#============================================
#これからの発展性（メモ）
#============================================
#今は、自分で人物を登録して増やしていく感じのアプリやけど、
#アカウント登録機能ができたら、フレンド交換した相手が図鑑に
#登録されていく形でも面白いかなと思った。
#
#各人物の登録時や編集時に、「家族」グループや「友達」グループ、
#「恋人」相手などを選択できるようになったら、相関図を作る時とかに面白そう。
#
#もっとシニカル（皮肉のある）なアプリにしてもいいかも。
#でもどうやって？アイデアがない。
#
#次、Render にデプロイするときに、PostgreSQL から Supabase に
#移行しようかな。
