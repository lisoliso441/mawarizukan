import { useEffect, useState } from "react";
import axios from "axios";

export default function App() {
  const [people, setPeople] = useState([]);
  const [form, setForm] = useState({ name: "", blood_type: "", mbti: "" });

  useEffect(() => {
    axios.get("http://127.0.0.1:5000/people").then(res => setPeople(res.data));
  }, []);

  const handleSubmit = e => {
    e.preventDefault();
    axios.post("http://127.0.0.1:5000/people", form).then(() => {
      setForm({ name: "", blood_type: "", mbti: "" });
      axios.get("http://127.0.0.1:5000/people").then(res => setPeople(res.data));
    });
  };

  return (
    <div className="p-6">
      <h1>まわり図鑑</h1>
      <form onSubmit={handleSubmit}>
        <input placeholder="名前" value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
        <input placeholder="血液型" value={form.blood_type} onChange={e => setForm({...form, blood_type: e.target.value})} />
        <input placeholder="MBTI" value={form.mbti} onChange={e => setForm({...form, mbti: e.target.value})} />
        <button type="submit">登録</button>
      </form>
      <ul>
        {people.map(p => (
          <li key={p.id}>{p.name} ({p.blood_type}/{p.mbti})</li>
        ))}
      </ul>
    </div>
  );
}
