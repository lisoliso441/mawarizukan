/* ===========================================
   MBTI / LOVE ラベル定義
=========================================== */
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

/* ===========================================
   グローバル状態
=========================================== */
let compatMode = false;
let selectedIds = [];
let diagnoseBtn = null;
let currentPeople = [];

/* ===========================================
   詳細表示
=========================================== */
async function fetchPersonData(id) {
  const res = await fetch(`/person/${id}`);
  return res.json();
}

async function showDetail(id) {
  const modal = document.getElementById("detail-modal");
  const detailBody = document.getElementById("detail-body");

  modal.style.display = "flex";
  detailBody.innerHTML = "<p>Loading...</p>";

  const data = await fetchPersonData(id);

  const mbtiLabel = data.mbti ? (MBTI_LABELS[data.mbti] || "-") : "-";
  const loveLabel = data.love_type ? (LOVE_LABELS[data.love_type] || "-") : "-";

  detailBody.innerHTML = `
    ${data.image_path
      ? `<img src="${data.image_path}" class="person-img">`
      : `<div class="person-placeholder">No Image</div>`}

    <h3>${data.name}</h3>

    <p>生年月日：${data.birth || "-"}</p>
    <p>血液型：${data.blood_type || "-"}</p>
    <p>MBTI：${mbtiLabel}</p>
    <p>ラブタイプ：${loveLabel}</p>
    <p>口癖：${data.phrase || "-"}</p>

    <div class="detail-btn-group">
      <a href="/edit/${data.id}" class="edit-btn">編集</a>

      <form method="post" action="/delete/${data.id}" class="delete-form"
            onsubmit="return confirm('本当に削除しますか？');">
        <button type="submit" class="delete-btn">削除</button>
      </form>
    </div>
  `;
}

/* ===========================================
   相性診断モード
=========================================== */
function setupCompatibilityMode() {
  const modeBtn = document.getElementById("compatModeBtn");

  modeBtn.onclick = () => {
    compatMode = !compatMode;

    if (!compatMode) {
      resetCompatibilityMode();
      alert("相性診断モードを終了しました。");
      return;
    }

    alert("相性診断モードになりました！2人を選んでください！");
  };
}


/* ===========================================
   相性診断結果
=========================================== */
function createCompatResultModal() {
  const modal = document.createElement("div");
  modal.id = "compat-result-modal";
  modal.style = `
    display:none; position:fixed; inset:0;
    background:rgba(0,0,0,0.6); justify-content:center; align-items:center;
    z-index:2000;
  `;
  modal.innerHTML = `
    <div style="background:white; padding:25px; width:360px;
                border-radius:15px; text-align:center; position:relative;">
      <button id="close-compat-btn"
              style="position:absolute; top:10px; right:10px; border:none;
                     background:none; font-size:20px; cursor:pointer;">✖</button>
      <div id="compat-result-body"><p>診断中...</p></div>
    </div>
  `;
  document.body.appendChild(modal);
  return modal;
}

async function showCompatibilityResult(id1, id2) {
  const modal =
    document.getElementById("compat-result-modal") ||
    createCompatResultModal();

  const body = modal.querySelector("#compat-result-body");
  modal.style.display = "flex";
  body.innerHTML = "<p>診断中...</p>";

  const res = await fetch("/compatibility_api", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id1, id2 })
  });

  const data = await res.json();

  body.innerHTML = `
    <h2>💞 相性診断結果 💞</h2>
    <p><b>${data.p1}</b> × <b>${data.p2}</b></p>

    <p style="margin-top:10px; font-size:1.1em;">
      <b>${data.mbti1}</b> × <b>${data.mbti2}</b>
    </p>

    <div style="margin:12px 0; padding:10px; background:#f7f7f7;
                border-radius:8px; font-size:0.95em;">
      ${data.mbti_comment}
    </div>

    <div style="margin-top:15px; font-size:1.3em;">
      MBTI相性：<b>${data.mbti_score}%</b>
    </div>

    <div class="compat-gauge">
      <div class="compat-gauge-fill" id="compatGaugeFill"></div>
    </div>

    <div style="margin-top:25px;">
      <h3>🧬 血液型相性</h3>

      <p style="font-size:1.1em;">
        <b>${data.blood1 || "-"}</b> × <b>${data.blood2 || "-"}</b>
      </p>

      <div style="margin-top:8px; font-size:1.3em;">
        血液型相性：<b>${data.blood_score}%</b>
      </div>

      <div class="compat-gauge">
        <div class="compat-gauge-fill" id="bloodGaugeFill"></div>
      </div>
    </div>
  `;

  const score = data.mbti_score;
  const gauge = document.getElementById("compatGaugeFill");
  gauge.style.width = `${score}%`;

  if (score >= 80) gauge.style.background = "#ff4081";
  else if (score >= 60) gauge.style.background = "#ff8a50";
  else if (score >= 40) gauge.style.background = "#ffd740";
  else gauge.style.background = "#b0bec5";

  modal.querySelector("#close-compat-btn").onclick = () => {
    modal.style.display = "none";
  };

  const bloodGauge = document.getElementById("bloodGaugeFill");
  bloodGauge.style.width = `${data.blood_score}%`;

  if (data.blood_score >= 80) bloodGauge.style.background = "#ff4081";
  else if (data.blood_score >= 60) bloodGauge.style.background = "#ff8a50";
  else if (data.blood_score >= 40) bloodGauge.style.background = "#ffd740";
  else bloodGauge.style.background = "#b0bec5";
}

/* ===========================================
   相性診断ボタン
=========================================== */
function showDiagnoseButton() {
  if (diagnoseBtn) return;

  diagnoseBtn = document.createElement("button");
  diagnoseBtn.textContent = "💗 診断する";
  diagnoseBtn.style = `
    position:fixed;
    bottom:20px; left:50%; transform:translateX(-50%);
    padding:12px 24px; background:#FF4081; color:white;
    border:none; border-radius:12px; font-size:1.2em;
    cursor:pointer; z-index:1500;
    box-shadow:0 4px 10px rgba(0,0,0,0.2);
  `;
  document.body.appendChild(diagnoseBtn);

  diagnoseBtn.onclick = () => {
    if (selectedIds.length === 2) {
      showCompatibilityResult(selectedIds[0], selectedIds[1]);
      resetCompatibilityMode();
    }
  };
}

function hideDiagnoseButton() {
  if (diagnoseBtn) {
    diagnoseBtn.remove();
    diagnoseBtn = null;
  }
}

/* ===========================================
   相性診断モードリセット
=========================================== */
function resetCompatibilityMode() {
  compatMode = false;
  selectedIds = [];

  document.querySelectorAll(".person-card")
    .forEach(c => c.style.border = "2px solid #ccc");

  hideDiagnoseButton();
}

/* ===========================================
   カードクリック
=========================================== */
async function handleCardClick(e) {
  const card = e.target.closest(".person-card");
  if (!card) return;

  const id = parseInt(card.dataset.id);

  if (compatMode) {
    if (selectedIds.includes(id)) {
      selectedIds = selectedIds.filter(x => x !== id);
      card.style.border = "2px solid #ccc";
    } else if (selectedIds.length < 2) {
      selectedIds.push(id);
      card.style.border = "3px solid #ff4081";
    }

    if (selectedIds.length === 2) showDiagnoseButton();
    else hideDiagnoseButton();

    return;
  }

  showDetail(id);
}

/* ===========================================
   フィルターモーダル
=========================================== */
async function applyFilter() {
  const formData = new FormData(document.getElementById("filterForm"));
  const selectedTags = [...formData.getAll("tags")].map(Number);

  const body = {
    name: formData.get("name") || "",
    blood_type: formData.get("blood_type") || "",
    mbti: formData.get("mbti") || "",
    love_type: formData.get("love_type") || "",
    tags: selectedTags
  };

  const res = await fetch("/filter", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  const people = await res.json();
  renderPeople(people);
  document.getElementById("filterModal").style.display = "none";
}

function setupFilterModal() {
  document.getElementById("openFilterBtn").onclick = () => {
    document.getElementById("filterModal").style.display = "flex";
  };
  document.getElementById("closeFilterBtn").onclick = () => {
    document.getElementById("filterModal").style.display = "none";
  };
  document.getElementById("applyFilterBtn").onclick = applyFilter;
}

/* ===========================================
   ソートモーダル
=========================================== */
function setupSortModal() {
  const sortBtn = document.getElementById("sortBtn");
  const sortModal = document.getElementById("sortModal");
  const sortApplyBtn = document.getElementById("sortApplyBtn");
  const sortCloseBtn = document.getElementById("sortCloseBtn");

  sortBtn.onclick = () => {
    sortModal.style.display = "flex";
  };

  sortCloseBtn.onclick = () => {
    sortModal.style.display = "none";
  };

  sortApplyBtn.onclick = () => {
    const key = document.getElementById("sortSelect").value;
    let sorted = [...currentPeople];

    if (key === "name") {
      sorted.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    } else if (key === "mbti") {
      sorted.sort((a, b) => (a.mbti || "").localeCompare(b.mbti || ""));
    } else if (key === "love_type") {
      sorted.sort((a, b) => (a.love_type || "").localeCompare(b.love_type || ""));
    } else if (key === "blood_type") {
      sorted.sort((a, b) => (a.blood_type || "").localeCompare(b.blood_type || ""));
    } else if (key === "tag") {
      sorted.sort((a, b) => {
        const at = a.tags && a.tags.length ? a.tags[0] : "";
        const bt = b.tags && b.tags.length ? b.tags[0] : "";
        return at.localeCompare(bt);
      });
    }

    renderPeople(sorted);
    sortModal.style.display = "none";
  };
}

/* ===========================================
   図鑑描画（Cloudinary 対応版）
=========================================== */
function renderPeople(people) {
  currentPeople = people;

  const grid = document.getElementById("people-grid");
  grid.innerHTML = "";

  if (!people.length) {
    grid.innerHTML = "<p>該当する人物がいません。</p>";
    return;
  }

  people.forEach(p => {
    grid.innerHTML += `
      <div class="person-card" data-id="${p.id}">
        ${p.image_path
          ? `<img src="${p.image_path}" class="person-img">`
          : `<div class="person-placeholder">No Image</div>`}
        <p class="person-name"><b>${p.name}</b></p>
      </div>
    `;
  });
}

/* ===========================================
   初期化
=========================================== */
function init() {
  setupCompatibilityMode();
  setupFilterModal();
  setupSortModal();

  document.getElementById("people-grid")
    .addEventListener("click", handleCardClick);

  document.getElementById("close-btn").onclick = () => {
    document.getElementById("detail-modal").style.display = "none";
  };

  document.getElementById("detail-modal").onclick = (e) => {
    if (e.target === e.currentTarget)
      e.currentTarget.style.display = "none";
  };
}

document.addEventListener("DOMContentLoaded", init);
