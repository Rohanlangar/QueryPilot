import React from 'react';
import Chip from '../common/Chip';
import { Sparkles } from 'lucide-react';

export default function SuggestedQuestions({ questions = [], onSelect }) {
  if (!questions || questions.length === 0) return null;

  return (
    <div className="suggested-questions">
      {questions.map((q, idx) => (
        <Chip
          key={idx}
          icon={Sparkles}
          onClick={() => onSelect(q)}
          variant="default"
        >
          {q}
        </Chip>
      ))}
    </div>
  );
}
