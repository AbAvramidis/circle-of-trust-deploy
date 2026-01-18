import { useState } from 'react';
import './NewGroupChatModal.css';

export default function NewGroupChatModal({ availableAdvisors, onClose, onCreate }) {
  const [selectedMembers, setSelectedMembers] = useState([]);

  const toggleMember = (advisorId) => {
    setSelectedMembers((prev) =>
      prev.includes(advisorId)
        ? prev.filter((id) => id !== advisorId)
        : [...prev, advisorId]
    );
  };

  const handleCreate = () => {
    if (selectedMembers.length > 0) {
      onCreate(selectedMembers);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Start New Group Chat</h2>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <p className="instruction">
            Select one or more council members to chat with:
          </p>

          <div className="members-list">
            {availableAdvisors.map((advisor) => (
              <div
                key={advisor.id}
                className={`member-option ${
                  selectedMembers.includes(advisor.id) ? 'selected' : ''
                }`}
                onClick={() => toggleMember(advisor.id)}
              >
                <input
                  type="checkbox"
                  checked={selectedMembers.includes(advisor.id)}
                  onChange={() => {}}
                />
                <div className="member-info">
                  <span className="member-name">{advisor.name}</span>
                  <span className="member-model">{advisor.model}</span>
                </div>
              </div>
            ))}
          </div>

          {availableAdvisors.length === 0 && (
            <div className="no-advisors">
              <p>No council members configured.</p>
              <p>Please configure your council first.</p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="cancel-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            className="create-btn"
            onClick={handleCreate}
            disabled={selectedMembers.length === 0}
          >
            Start Chat ({selectedMembers.length} selected)
          </button>
        </div>
      </div>
    </div>
  );
}
