import { Workbook } from '@oai/artifact-tool';
console.log(Workbook.create().help('*', { search: 'insert.*row|row.*insert|delete.*row', include: 'index,examples,notes', maxChars: 3000 }).ndjson);
