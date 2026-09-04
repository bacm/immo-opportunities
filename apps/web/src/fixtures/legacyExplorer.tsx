/**
 * v0.1 explorer fixture kept until v0.7 for isolated visual development.
 * It is deliberately not imported by the real application entrypoint.
 */
export const legacyCandidates = [
  { id: 'opp-2984', address: '14 rue des Tilleuls', city: 'Cesson-Sévigné', score: 87 },
  { id: 'opp-1942', address: '8 allée des Chênes', city: 'Saint-Grégoire', score: 82 },
  { id: 'opp-3166', address: '31 avenue du Général Leclerc', city: 'Bruz', score: 78 },
  { id: 'opp-2077', address: '5 impasse de la Fontaine', city: 'Betton', score: 74 },
  { id: 'opp-889', address: '22 rue de Bretagne', city: 'Chantepie', score: 69 },
  { id: 'opp-2261', address: '17 rue du Clos', city: 'Pacé', score: 64 },
] as const

export function LegacySvgMapFixture() {
  return (
    <svg viewBox="0 0 520 460" aria-label="Fixture de carte SVG historique">
      <rect width="520" height="460" fill="#eef1eb" />
      <path d="M0 224 C119 198 205 185 520 137" fill="none" stroke="#cad2ca" />
      <path d="M-20 284 C145 245 250 205 540 214" fill="none" stroke="#fff" strokeWidth="8" />
      <polygon points="183,145 258,133 273,205 194,220" fill="#cae36b55" stroke="#256452" />
    </svg>
  )
}
