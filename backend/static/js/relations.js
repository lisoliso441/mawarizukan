/* ============================================
   関係性ネットワーク グラフ描画
============================================ */

document.addEventListener("DOMContentLoaded", async () => {
  const container = document.getElementById("relation-network");
  if (!container) return; // このページでないなら描画しない

  /* ------------------------------
     1. API からデータ取得
  ------------------------------ */
  const res = await fetch("/api/relations");
  const data = await res.json();

  const people = data.people;
  const relations = data.relations;

  /* ------------------------------
     2. ノード生成（人物）
  ------------------------------ */
  const nodes = people.map(p => ({
    id: p.id,
    label: p.name,
    shape: "circularImage",
    image: p.image || "/static/default_icon.png",
    size: 40,
    font: { size: 14 }
  }));

  /* ------------------------------
     3. 関係タイプごとの線色
  ------------------------------ */
  const REL_COLORS = {
    friend: "#4CAF50",          // 友達
    senpai_kohai: "#2196F3",    // 先輩・後輩
    family: "#E91E63",          // 家族
    lover: "#ff4de1ff",         // 恋人
    //旧データ互換
    senpai: "#2196F3",
    kohai: "#2196F3"
  };
  const DEFAULT_REL_COLOR = "#6bbf80";

  /* ------------------------------
     4. 線データ生成
     - 太さ：strength（1〜5）
     - 色：relation_type に応じて
  ------------------------------ */
  const edges = relations.map(r => {
    const edgeColor = REL_COLORS[r.type] || DEFAULT_REL_COLOR;

    return {
      id: r.id,
      from: r.source,
      to: r.target,
      width: r.strength * 1.2,
      color: {
        color: edgeColor,
        highlight: edgeColor
      }
    };
  });

  /* ------------------------------
     5. ネットワーク描画
  ------------------------------ */
  const network = new vis.Network(
    container,
    { nodes, edges },
    {
      physics: {
        enabled: true,
        stabilization: true
      },
      interaction: {
        hover: true
      },
      nodes: {
        borderWidth: 2
      }
    }
  );

  /* ------------------------------
     6. ノードクリック → 詳細モーダル
  ------------------------------ */
  network.on("click", params => {
    if (params.nodes.length > 0) {
      const id = params.nodes[0];
      showDetail(id); // 既存の詳細モーダルを利用
    }
  });
});
