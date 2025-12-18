/* ============================================================
   詳細モーダル共通ロジック
============================================================ */
const MBTI_LABELS = {
  "INTJ": "INTJ（建築家）","INTP": "INTP（論理学者）","ENTJ": "ENTJ（指揮官）","ENTP": "ENTP（討論者）",
  "INFJ": "INFJ（提唱者）","INFP": "INFP（仲介者）","ENFJ": "ENFJ（主人公）","ENFP": "ENFP（活動家）",
  "ISTJ": "ISTJ（管理者）","ISFJ": "ISFJ（擁護者）","ESTJ": "ESTJ（幹部）","ESFJ": "ESFJ（領事館）",
  "ISTP": "ISTP（巨匠）","ISFP": "ISFP（冒険者）","ESTP": "ESTP（起業家）","ESFP": "ESFP（エンターテイナー）"
};

const LOVE_LABELS = {
  "LCRO": "LCRO（ボス猫）","LCRE": "LCRE（隠れベイビー）","LCPO": "LCPO（主役体質）","LCPE": "LCPE（ツンデレヤンキー）",
  "LARO": "LARO（憧れの先輩）","LARE": "LARE（カリスマバランサー）","LAPO": "LAPO（パーフェクトカメレオン）","LAPE": "LAPE（キャプテンライオン）",
  "FCRO": "FCRO（ロマンスマジシャン）","FCRE": "FCRE（ちゃっかりうさぎ）","FCPO": "FCPO（恋愛モンスター）","FCPE": "FCPE（忠犬ハチ公）",
  "FARO": "FARO（不思議生命体）","FARE": "FARE（敏腕マネージャー）","FAPO": "FAPO（デビル天使）","FAPE": "FAPE（最後の恋人）"
};

async function fetchPersonData(id) {
  const res = await fetch(`/person/${id}`);
  if (!res.ok) throw new Error("Failed to fetch detail data");
  return res.json();
}

async function showDetail(id) {
  const modal = document.getElementById("detail-modal");
  const detailBody = document.getElementById("detail-info");

  if (!modal || !detailBody) return;

  modal.style.display = "flex";
  detailBody.innerHTML = "<p>Loading...</p>";

  try {
    const data = await fetchPersonData(id);

    const mbtiLabel = data.mbti ? (MBTI_LABELS[data.mbti] || "-") : "-";
    const loveLabel = data.love_type ? (LOVE_LABELS[data.love_type] || "-") : "-";

    const tagHtml =
      Array.isArray(data.tags) && data.tags.length
        ? data.tags.map(t => `<span class="tag-pill">${t}</span>`).join("")
        : "-";

    detailBody.innerHTML = `
      <div class="detail-header">
        <div class="detail-icon-area">
          ${data.image_path
            ? `<img src="${data.image_path}" class="detail-image">`
            : `<div class="person-placeholder detail-image"></div>`}
        </div>

        <div class="detail-phrase-bubble">
          ${data.phrase || "・・・"}
        </div>
      </div>

      <div class="profile-row">
        <div class="label">名前</div>
        <div class="value">${data.name}</div>
      </div>

      <div class="profile-row">
        <div class="label">読み</div>
        <div class="value">${data.reading || "-"}</div>
      </div>

      <div class="profile-row">
        <div class="label">生年月日</div>
        <div class="value">${data.birth || "-"}</div>
      </div>

      <div class="profile-row">
        <div class="label">血液型</div>
        <div class="value">${data.blood_type || "-"}</div>
      </div>

      <div class="profile-row">
        <div class="label">MBTI</div>
        <div class="value">${mbtiLabel}</div>
      </div>

      <div class="profile-row">
        <div class="label">ラブタイプ</div>
        <div class="value">${loveLabel}</div>
      </div>

      <div class="profile-row">
        <div class="label">グループタグ</div>
        <div class="value tags">${tagHtml}</div>
      </div>

      <div class="detail-btn-group">
        <a href="/edit/${data.id}" class="edit-btn">編集</a>

        <form method="post" action="/delete/${data.id}" class="delete-form"
              onsubmit="return confirm('本当に削除しますか？');">
          <button type="submit" class="delete-btn">削除</button>
        </form>
      </div>
    `;
  } catch (err) {
    console.error(err);
    detailBody.innerHTML = "<p>詳細を取得できませんでした。</p>";
  }
}

function hideDetailModal() {
  const modal = document.getElementById("detail-modal");
  if (modal) modal.style.display = "none";
}

function setupDetailModal() {
  const modal = document.getElementById("detail-modal");
  if (!modal) return;

  const closeBtn = modal.querySelector("#close-btn");
  if (closeBtn) closeBtn.onclick = hideDetailModal;

  modal.addEventListener("click", e => {
    if (e.target === modal) hideDetailModal();
  });
}

document.addEventListener("DOMContentLoaded", setupDetailModal);
