// Muestra un cuestionario en HTML plano, sin estilos.
const ITEM_TYPES = {
  escala_likert: 'Escala Likert',
  seleccion_multiple: 'Selección múltiple',
  verdadero_falso: 'Verdadero / falso',
  desarrollo: 'Desarrollo',
  emparejamiento: 'Emparejamiento',
}

function QuestionnaireView({ questionnaire }) {
  return (
    <div>
      <h3>{questionnaire.titulo ?? '(sin título)'}</h3>
      <p>
        Idioma: {questionnaire.idioma} | Ítems: {questionnaire.total_items}
      </p>
      <ol>
        {questionnaire.items.map((item) => (
          <li key={item.numero}>
            <p>
              <strong>{item.enunciado}</strong>
              <br />
              Tipo: {ITEM_TYPES[item.tipo] ?? item.tipo}
            </p>
            {item.alternativas.length > 0 && (
              <ul>
                {item.alternativas.map((option) => (
                  <li key={`${option.valor}-${option.texto}`}>
                    {option.valor}) {option.texto}
                    {option.valor === item.respuesta_correcta && ' ← respuesta correcta'}
                  </li>
                ))}
              </ul>
            )}
            {item.respuesta_correcta !== null && (
              <p>Respuesta correcta: {String(item.respuesta_correcta)}</p>
            )}
          </li>
        ))}
      </ol>
    </div>
  )
}

export default QuestionnaireView
