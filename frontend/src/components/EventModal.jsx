import { useState } from "react";

export default function EventModal({ event, onClose, onSave }) {
  const [title, setTitle] = useState(event?.title || "");
  const [start, setStart] = useState(event?.start || "");
  const [end, setEnd] = useState(event?.end || "");

  const handleSubmit = () => {
    if (!title.trim()) {
      alert("Введи назву події");
      return;
    }

    onSave({
      title,
      start,
      end,
    });
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>Створити / редагувати подію</h3>

        <input
          placeholder="Назва"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        <input
          type="datetime-local"
          value={start}
          onChange={(e) => setStart(e.target.value)}
        />

        <input
          type="datetime-local"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
        />

        <div className="modal-buttons">
          <button type="button" onClick={onClose}>
            Скасувати
          </button>

          <button type="button" onClick={handleSubmit}>
            Зберегти
          </button>
        </div>
      </div>
    </div>
  );
}