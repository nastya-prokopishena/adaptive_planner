import { useState } from "react"

export default function EventModal({ event, onClose, onSave }) {
  const [title, setTitle] = useState(event?.title || "")
  const [start, setStart] = useState(event?.start || "")
  const [end, setEnd] = useState(event?.end || "")

  const handleSubmit = () => {
    onSave({ title, start, end })
  }

  return (
    <div className="modal-overlay">

      <div className="modal">

        <h3>Create / Edit Event</h3>

        <input
          placeholder="Title"
          value={title}
          onChange={e => setTitle(e.target.value)}
        />

        <input
          type="datetime-local"
          value={start}
          onChange={e => setStart(e.target.value)}
        />

        <input
          type="datetime-local"
          value={end}
          onChange={e => setEnd(e.target.value)}
        />

        <div className="modal-buttons">
          <button onClick={onClose}>Cancel</button>
          <button onClick={handleSubmit}>Save</button>
        </div>

      </div>

    </div>
  )
}