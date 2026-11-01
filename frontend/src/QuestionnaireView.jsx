// Muestra un cuestionario: título, idioma, ítems con su tipo, alternativas y respuesta correcta.
const ITEM_TYPES = {
  escala_likert: 'Escala Likert',
  seleccion_multiple: 'Selección múltiple',
  verdadero_falso: 'Verdadero / falso',
  desarrollo: 'Desarrollo',
  emparejamiento: 'Emparejamiento',
}

const LANGUAGES = { es: 'Español', it: 'Italiano', en: 'Inglés' }

function QuestionnaireView({ questionnaire }) {
  return (
    <div>
      <h3 className="questionnaire-title">{questionnaire.titulo ?? 'Cuestionario sin título'}</h3>
      <div className="questionnaire-meta">
        <span className="badge">{LANGUAGES[questionnaire.idioma] ?? questionnaire.idioma}</span>
        <span className="badge badge-muted">{questionnaire.total_items} ítems</span>
      </div>
      <ol className="items">
        {questionnaire.items.map((item) => (
          <li key={item.numero} className="item">
            <span className="item-number">{item.numero}</span>
            <div>
              <p className="item-statement">{item.enunciado}</p>
              <span className="badge badge-muted">{ITEM_TYPES[item.tipo] ?? item.tipo}</span>
              {item.alternativas.length > 0 && (
                <ul className="item-options">
                  {item.alternativas.map((option) => {
                    const correct = option.valor === item.respuesta_correcta
                    return (
                      <li key={`${option.valor}-${option.texto}`} className={`item-option${correct ? ' correct' : ''}`}>
                        <span className="item-option-value">{option.valor}</span>
                        <span>{option.texto}</span>
                        {correct && <span aria-label="respuesta correcta">✓</span>}
                      </li>
                    )
                  })}
                </ul>
              )}
              {item.respuesta_correcta !== null && (
                <p className="item-answer">Respuesta correcta: {String(item.respuesta_correcta)}</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

export default QuestionnaireView
