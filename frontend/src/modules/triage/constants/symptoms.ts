/**
 * Constantes de sintomas compartilhadas, espelhando backend/app/triage/constants.py.
 */

export interface SymptomOption {
  value: string
  label: string
}

export const PRIMARY_SYMPTOMS: readonly string[] = [
  'FEBRE',
  'DOR_DE_CABECA',
  'NAUSEA',
  'TOSSE',
  'DOR_ABDOMINAL',
  'DOR_DE_GARGANTA',
  'CONGESTAO_NASAL',
  'DOR_DE_OUVIDO',
  'ESPIRROS',
  'COCEIRA',
  'VERMELHIDAO_DA_PELE',
  'MANCHAS_NA_PELE',
  'INCHACO',
  'DOR_LOCAL',
  'FALTA_DE_AR',
  'DOR_NO_PEITO',
  'CHIADO_NO_PEITO',
  'PALPITACAO',
  'TONTURA',
  'SUOR_EXCESSIVO',
  'DIARREIA',
  'DOR_MUSCULAR',
  'CANSAÇO',
] as const

export const SYMPTOM_OPTIONS: readonly SymptomOption[] = [
  { value: 'FEBRE', label: 'Febre' },
  { value: 'DOR_DE_CABECA', label: 'Dor de cabeça' },
  { value: 'NAUSEA', label: 'Náusea' },
  { value: 'TOSSE', label: 'Tosse' },
  { value: 'DOR_ABDOMINAL', label: 'Dor abdominal' },
  { value: 'DOR_DE_GARGANTA', label: 'Dor de garganta' },
  { value: 'CONGESTAO_NASAL', label: 'Congestão nasal' },
  { value: 'DOR_DE_OUVIDO', label: 'Dor de ouvido' },
  { value: 'ESPIRROS', label: 'Espirros' },
  { value: 'COCEIRA', label: 'Coceira' },
  { value: 'VERMELHIDAO_DA_PELE', label: 'Vermelhidão da pele' },
  { value: 'MANCHAS_NA_PELE', label: 'Manchas na pele' },
  { value: 'INCHACO', label: 'Inchaço' },
  { value: 'DOR_LOCAL', label: 'Dor local' },
  { value: 'FALTA_DE_AR', label: 'Falta de ar' },
  { value: 'DOR_NO_PEITO', label: 'Dor no peito' },
  { value: 'CHIADO_NO_PEITO', label: 'Chiado no peito' },
  { value: 'PALPITACAO', label: 'Palpitação' },
  { value: 'TONTURA', label: 'Tontura' },
  { value: 'SUOR_EXCESSIVO', label: 'Suor excessivo' },
  { value: 'DIARREIA', label: 'Diarreia' },
  { value: 'DOR_MUSCULAR', label: 'Dor muscular' },
  { value: 'CANSAÇO', label: 'Cansaço' },
] as const
