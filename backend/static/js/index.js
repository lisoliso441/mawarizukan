/* ============================================================
   グローバル状態
============================================================ */
let compatMode = false;
let selectedIds = [];
let diagnoseBtn = null;
let currentPeople = [];

/* ============================================================
   ユーティリティ / 初期データ読み込み
============================================================ */
function loadInitialPeople() {
  const el = document.getElementById("initial-people-data");
  if (!el) return [];
  try {
    return JSON.parse(el.textContent);
  } catch {
    return [];
  }
}

/* ============================================================
   相性診断モード
============================================================ */
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

/* ============================================================
   相性診断（結果モーダル生成）
============================================================ */
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
  const mbti1Label = data.mbti1 ? (MBTI_LABELS[data.mbti1] || data.mbti1) : "-";
  const mbti2Label = data.mbti2 ? (MBTI_LABELS[data.mbti2] || data.mbti2) : "-";
  const blood1Label = data.blood1 ? data.blood1 : "???";
  const blood2Label = data.blood2 ? data.blood2 : "???";
  const bloodScoreText =
    typeof data.blood_score === "number" ? `${data.blood_score}%` : "???";
  const defaultIcon = "/static/default_icon.png";
  const p1Image = data.p1_image || defaultIcon;
  const p2Image = data.p2_image || defaultIcon;

  body.innerHTML = `
    <h2>💞 相性診断結果 💞</h2>
    <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; margin:8px 0 4px;">
      <div style="display:flex; align-items:center; gap:10px;">
        <img src="${p1Image}" alt="${data.p1}" style="width:48px; height:48px; border-radius:50%; object-fit:cover;">
        <span style="font-size:1.3em;"><b>${data.p1}</b></span>
      </div>
      <span style="font-size:1.4em;">×</span>
      <div style="display:flex; align-items:center; gap:10px;">
        <span style="font-size:1.3em;"><b>${data.p2}</b></span>
        <img src="${p2Image}" alt="${data.p2}" style="width:48px; height:48px; border-radius:50%; object-fit:cover;">
      </div>
    </div>

    <hr style="border:none; border-top:1px solid #eee; margin:12px 0;">

    <p style="margin-top:10px; font-size:1.1em;">
      <b>${mbti1Label}</b> × <b>${mbti2Label}</b>
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

    <hr style="border:none; border-top:1px solid #eee; margin:22px 0 15px;">

    <div style="margin-top:5px;">
      <h3>🧬 血液型相性</h3>

      <p style="font-size:1.1em;">
        <b>${blood1Label}</b> × <b>${blood2Label}</b>
      </p>

      <div style="margin-top:8px; font-size:1.3em;">
        血液型相性：<b>${bloodScoreText}</b>
      </div>

      <div class="compat-gauge">
        <div class="compat-gauge-fill" id="bloodGaugeFill"></div>
      </div>
    </div>
  `;

  const gauge = document.getElementById("compatGaugeFill");
  gauge.style.width = `${data.mbti_score}%`;

  if (data.mbti_score >= 80) gauge.style.background = "#ff4081";
  else if (data.mbti_score >= 60) gauge.style.background = "#ff8a50";
  else if (data.mbti_score >= 40) gauge.style.background = "#ffd740";
  else gauge.style.background = "#b0bec5";

  modal.querySelector("#close-compat-btn").onclick = () => {
    modal.style.display = "none";
  };

  const bloodGauge = document.getElementById("bloodGaugeFill");
  if (typeof data.blood_score === "number") {
    bloodGauge.style.width = `${data.blood_score}%`;
    if (data.blood_score >= 80) bloodGauge.style.background = "#ff4081";
    else if (data.blood_score >= 60) bloodGauge.style.background = "#ff8a50";
    else if (data.blood_score >= 40) bloodGauge.style.background = "#ffd740";
    else bloodGauge.style.background = "#b0bec5";
  } else {
    bloodGauge.style.width = "0%";
    bloodGauge.style.background = "#b0bec5";
  }
}

/* ============================================================
   相性診断ボタン
============================================================ */
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

/* ============================================================
   相性診断モードのリセット
============================================================ */
function resetCompatibilityMode() {
  compatMode = false;
  selectedIds = [];

  document.querySelectorAll(".person-card")
    .forEach(c => c.style.border = "2px solid #ccc");

  hideDiagnoseButton();
}

/* ============================================================
   図鑑カードクリック
============================================================ */
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

/* ============================================================
   フィルター機能
============================================================ */
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
  const filterModal = document.getElementById("filterModal");
  const closeFilterBtnTop = document.getElementById("closeFilterBtnTop");

  document.getElementById("openFilterBtn").onclick = () => {
    filterModal.style.display = "flex";
  };
  if (closeFilterBtnTop) {
    closeFilterBtnTop.onclick = () => {
      filterModal.style.display = "none";
    };
  }
  document.getElementById("applyFilterBtn").onclick = applyFilter;
}

/* ============================================================
   ソート機能
============================================================ */
function setupSortModal() {
  const sortBtn = document.getElementById("sortBtn");
  const sortModal = document.getElementById("sortModal");
  const sortApplyBtn = document.getElementById("sortApplyBtn");
  const sortCloseBtnTop = document.getElementById("sortCloseBtnTop");

  sortBtn.onclick = () => {
    sortModal.style.display = "flex";
  };

  if (sortCloseBtnTop) {
    sortCloseBtnTop.onclick = () => {
      sortModal.style.display = "none";
    };
  }

  sortApplyBtn.onclick = () => {
    const key = document.getElementById("sortSelect").value;
    let sorted = [...currentPeople];

    if (key === "reading") {
      sorted.sort((a, b) => (a.reading || "").localeCompare(b.reading || ""));
    }

    if (key === "birth") {
      sorted.sort((a, b) => {
        const da = a.birth || "9999-12-31";
        const db = b.birth || "9999-12-31";
        return da.localeCompare(db);
      });
    }

    if (key === "id") {
      sorted.sort((a, b) => a.id - b.id);
    }

    currentPeople = sorted;
    renderPeople(sorted);
    sortModal.style.display = "none";
  };
}

/* ============================================================
   図鑑一覧表示
============================================================ */
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

/* ============================================================
   初期化
============================================================ */
function init() {
  currentPeople = loadInitialPeople();

  setupCompatibilityMode();
  setupFilterModal();
  setupSortModal();

  document.getElementById("people-grid")
    .addEventListener("click", handleCardClick);
}

document.addEventListener("DOMContentLoaded", init);
