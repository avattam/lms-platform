import React from 'react';

/**
 * Formats inline Markdown (bold, italic, inline code)
 */
function renderInline(text) {
  if (!text) return null;

  // Split text by inline code, bold, and italic markers
  const parts = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining.length > 0) {
    // Check for inline code `code`
    const codeMatch = remaining.match(/^(.*?)`([^`]+)`(.*)$/s);
    if (codeMatch) {
      const [, before, codeText, after] = codeMatch;
      if (before) parts.push(...renderBoldItalic(before, keyIdx++));
      parts.push(<code key={`code-${keyIdx++}`} className="markdown-inline-code">{codeText}</code>);
      remaining = after;
      continue;
    }

    parts.push(...renderBoldItalic(remaining, keyIdx++));
    break;
  }

  return parts;
}

function renderBoldItalic(text, baseKey) {
  const elements = [];
  // Regex for **bold** and *italic*
  const tokens = text.split(/(\*\*.*?\*\*|\*.*?\*)/g);

  tokens.forEach((token, idx) => {
    if (!token) return;
    if (token.startsWith('**') && token.endsWith('**') && token.length > 4) {
      elements.push(<strong key={`b-${baseKey}-${idx}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('*') && token.endsWith('*') && token.length > 2) {
      elements.push(<em key={`i-${baseKey}-${idx}`}>{token.slice(1, -1)}</em>);
    } else {
      elements.push(token);
    }
  });

  return elements;
}

/**
 * High-performance Markdown & HTML block parser
 */
export default function FormattedMessage({ content }) {
  if (!content) return null;

  const lines = content.split('\n');
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // 1. Code block ```
    if (line.trim().startsWith('```')) {
      const codeLines = [];
      const lang = line.trim().slice(3);
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      blocks.push(
        <div key={`code-block-${i}`} className="markdown-code-wrapper">
          {lang && <div className="code-lang-tag">{lang}</div>}
          <pre className="markdown-code-block">
            <code>{codeLines.join('\n')}</code>
          </pre>
        </div>
      );
      continue;
    }

    // 2. Markdown Table detection (starts with | and contains |)
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      const tableRows = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableRows.push(lines[i].trim());
        i++;
      }

      if (tableRows.length >= 2) {
        // Filter out separator row (|---|---|)
        const headerRow = tableRows[0];
        const hasSep = tableRows[1] && tableRows[1].includes('---');
        const bodyRows = hasSep ? tableRows.slice(2) : tableRows.slice(1);

        const parseCells = rowStr =>
          rowStr
            .split('|')
            .slice(1, -1)
            .map(c => c.trim());

        const headers = parseCells(headerRow);

        blocks.push(
          <div key={`table-${i}`} className="markdown-table-wrapper">
            <table className="markdown-table">
              <thead>
                <tr>
                  {headers.map((h, hIdx) => (
                    <th key={hIdx}>{renderInline(h)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bodyRows.map((rStr, rIdx) => {
                  const cells = parseCells(rStr);
                  return (
                    <tr key={rIdx}>
                      {cells.map((cell, cIdx) => (
                        <td key={cIdx}>{renderInline(cell)}</td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    // 3. Headings (###, ##, #)
    if (line.startsWith('### ')) {
      blocks.push(<h3 key={`h3-${i}`} className="markdown-h3">{renderInline(line.slice(4))}</h3>);
      i++;
      continue;
    }
    if (line.startsWith('## ')) {
      blocks.push(<h2 key={`h2-${i}`} className="markdown-h2">{renderInline(line.slice(3))}</h2>);
      i++;
      continue;
    }
    if (line.startsWith('# ')) {
      blocks.push(<h1 key={`h1-${i}`} className="markdown-h1">{renderInline(line.slice(2))}</h1>);
      i++;
      continue;
    }

    // 4. Bulleted List (- , * , + )
    if (/^\s*[-*+]\s+/.test(line)) {
      const listItems = [];
      while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
        const itemText = lines[i].replace(/^\s*[-*+]\s+/, '');
        listItems.push(itemText);
        i++;
      }
      blocks.push(
        <ul key={`ul-${i}`} className="markdown-ul">
          {listItems.map((item, itemIdx) => (
            <li key={itemIdx}>{renderInline(item)}</li>
          ))}
        </ul>
      );
      continue;
    }

    // 5. Numbered List (1. , 2. )
    if (/^\s*\d+\.\s+/.test(line)) {
      const listItems = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        const itemText = lines[i].replace(/^\s*\d+\.\s+/, '');
        listItems.push(itemText);
        i++;
      }
      blocks.push(
        <ol key={`ol-${i}`} className="markdown-ol">
          {listItems.map((item, itemIdx) => (
            <li key={itemIdx}>{renderInline(item)}</li>
          ))}
        </ol>
      );
      continue;
    }

    // 6. Regular Paragraph or empty line
    if (line.trim() === '') {
      blocks.push(<div key={`space-${i}`} className="markdown-spacer" />);
    } else {
      blocks.push(<p key={`p-${i}`} className="markdown-p">{renderInline(line)}</p>);
    }
    i++;
  }

  return <div className="formatted-message-container">{blocks}</div>;
}
