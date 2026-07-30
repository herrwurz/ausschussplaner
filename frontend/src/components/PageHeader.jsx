/**
 * Einheitlicher Seitenkopf: Titel, optionale Beschreibung, Actions.
 */
export default function PageHeader({ title, description, actions }) {
  return (
    <div className="page-header section-header">
      <div className="page-header__titles">
        <h2>{title}</h2>
        {description && <p className="page-header__desc">{description}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </div>
  )
}
