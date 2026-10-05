const orcidInput = document.querySelector('#orcid');
const ingestButton = document.querySelector('#ingest');
const statusBox = document.querySelector('#status');
const summary = document.querySelector('#summary');
const messages = document.querySelector('#messages');
const chatForm = document.querySelector('#chat-form');
const questionInput = document.querySelector('#question');

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {'Content-Type': 'application/json'},
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[character]);
}

function addMessage(kind, text, sources = [], metadata = null) {
  const article = document.createElement('article');
  article.className = `message ${kind}`;
  article.innerHTML = `<p>${escapeHtml(text)}</p>`;
  if (sources.length) {
    const list = document.createElement('ul');
    list.className = 'sources';
    sources.forEach(source => {
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = source.url;
      link.target = '_blank';
      link.rel = 'noreferrer';
      link.textContent = source.label;
      item.appendChild(link);
      list.appendChild(item);
    });
    article.appendChild(list);
  }
  if (metadata) {
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.textContent = `${metadata.mode} · ${metadata.status.replaceAll('_', ' ')}`;
    article.appendChild(meta);
  }
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
}

function renderReport(report) {
  const statHtml = `
    <div class="stats">
      <div><strong>${report.stats.publications}</strong><span>publications</span></div>
      <div><strong>${report.stats.taxa}</strong><span>taxa</span></div>
      <div><strong>${report.stats.evidence_records}</strong><span>evidence links</span></div>
    </div>`;
  const organismHtml = report.organisms.length
    ? report.organisms.map(organism => `
      <details>
        <summary>
          <span><strong>${escapeHtml(organism.scientific_name)}</strong><small>TAXID ${organism.taxid}</small></span>
          <span class="confidence">${Math.round(organism.maximum_confidence * 100)}%</span>
        </summary>
        ${organism.evidence.map(item => `
          <a class="evidence-card" href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">
            <span>${escapeHtml(item.title)}</span>
            <small>PMID ${escapeHtml(item.pmid)} · ${escapeHtml(item.publication_type)} · ${item.year || 'year unavailable'}</small>
          </a>`).join('')}
      </details>`).join('')
    : '<p class="empty">No NCBI-linked taxonomy evidence was found. This does not establish lack of experience.</p>';
  summary.innerHTML = statHtml + `<div class="organisms">${organismHtml}</div>`;
}

ingestButton.addEventListener('click', async () => {
  ingestButton.disabled = true;
  statusBox.className = 'status loading';
  statusBox.textContent = 'Retrieving PubMed records and NCBI taxonomy links…';
  try {
    const result = await requestJson('/api/researchers/ingest', {
      method: 'POST', body: JSON.stringify({orcid: orcidInput.value, limit: 10})
    });
    statusBox.className = 'status success';
    statusBox.textContent = `Retrieved ${result.publications_found} publications and ${result.evidence_records} evidence links across ${result.taxa_found} taxa.`;
    const report = await requestJson(`/api/researchers/${encodeURIComponent(result.orcid)}/report`);
    renderReport(report);
  } catch (error) {
    statusBox.className = 'status error';
    statusBox.textContent = error.message;
  } finally {
    ingestButton.disabled = false;
  }
});

chatForm.addEventListener('submit', async event => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;
  addMessage('user', question);
  questionInput.value = '';
  try {
    const result = await requestJson('/api/chat', {
      method: 'POST',
      body: JSON.stringify({orcid: orcidInput.value, question}),
    });
    addMessage('assistant', result.answer, result.sources, {
      mode: result.response_mode,
      status: result.evidence_status,
    });
  } catch (error) {
    addMessage('assistant error-message', error.message);
  }
});
