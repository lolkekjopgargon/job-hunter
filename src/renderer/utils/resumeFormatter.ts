/**
 * resumeFormatter.ts
 * Cleans up raw and parsed HeadHunter resume titles.
 * Removes English metadata fragments (e.g., 'Permanent job, part-time job', 'At the employer\'s location')
 * and formats cleanly: "Название резюме — 150 000 ₽" or "Название резюме".
 */

export function formatResumeTitle(rawTitle: string): string {
  if (!rawTitle) return 'Резюме';

  let text = rawTitle.trim();

  // 1. Remove leading/inline English schedule and employment prefixes
  text = text.replace(/^(?:Permanent job|Part-time job|Full day|Remote work|Shift schedule|Fly-in fly-out)[,\s]*/gi, '');
  text = text.replace(/(?:Permanent job|part-time job|Full day|Remote work|Shift schedule|Fly-in fly-out)[,\s]*/gi, '');

  // 2. Remove trailing location or system notes
  text = text.replace(/(?:At the employer\'s location|Remote and more|Many people don\'t see your resume).*$/gi, '');

  // 3. Extract salary if present at the end or embedded
  const salaryMatch = text.match(/(\d[\d\s\u2009\xa0]*\s*₽)/);
  const salary = salaryMatch ? salaryMatch[1].replace(/[\u2009\xa0]/g, ' ').trim() : '';

  // 4. Extract pure title without the salary part
  let titleOnly = text;
  if (salaryMatch && salaryMatch.index !== undefined) {
    titleOnly = text.substring(0, salaryMatch.index).trim();
  }

  // Strip remaining punctuation/bullets
  titleOnly = titleOnly.replace(/[·•,\-—\s]+$/, '').trim();

  if (titleOnly && salary) {
    return `${titleOnly} — ${salary}`;
  }

  return titleOnly || text;
}
