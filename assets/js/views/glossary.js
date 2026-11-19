import { db, REVIEW, stats } from '../data.js';
import { glossaryMatch } from '../search.js';
import { esc, icon, itemHref } from '../ui.js';

const sorted = () => db.glossary.slice().sort((a, b) => a.standardTerm.localeCompare(b.standardTerm, 'ko'));
const row = (g) => `<tr>
  <td data-l="신용어"><strong>${g.itemId && db.item.get(g.itemId) ? `<a href="${itemHref(g.itemId)}">${esc(g.standardTerm)}</a>` : esc(g.standardTerm)}</strong></td>
  <td data-l="구용어">${esc((g.oldTerm || []).join(', ')) || '—'}</td>
  <td data-l="영어">${esc(g.englishTerm || '—')}</td>
  <td data-l="라틴어"><i lang="la">${esc(g.latinTerm || '—')}</i></td>
  <td data-l="뜻">${esc(g.definition || '')}</td></tr>`;

export function glossaryView(params) {
  const q = params.get('q') || '';
  const rows = sorted().filter((g) => glossaryMatch(g, q));
  const html = `
  <header class="page-head">
    <p class="eyebrow">Glossary</p>
    <h1 class="page-title">용어집</h1>
    <p class="page-sub">신용어를 기준으로 구용어·영어·라틴어를 함께 정리했습니다. 표기는 대한해부학회 용어집과 대조해 검토해야 합니다.</p>
  </header>
  <div class="search-input search-inline">${icon('search')}<input type="search" value="${esc(q)}" placeholder="용어 필터 — 굽힘, 외전, flexion, ㄱㅉㄷㄹ" aria-label="용어 필터" data-gloss-filter></div>
  <p class="result-count" aria-live="polite">${rows.length}개 용어</p>
  <div class="table-wrap">
    <table class="gloss">
      <thead><tr><th>신용어</th><th>구용어</th><th>영어</th><th>라틴어</th><th>뜻</th></tr></thead>
      <tbody>${rows.map(row).join('')}</tbody>
    </table>
  </div>`;
  function mount(root) {
    const input = root.querySelector('[data-gloss-filter]');
    input.addEventListener('input', () => {
      history.replaceState(null, '', `#/glossary${input.value ? `?q=${encodeURIComponent(input.value)}` : ''}`);
      const hits = sorted().filter((g) => glossaryMatch(g, input.value));
      root.querySelector('tbody').innerHTML = hits.map(row).join('');
      root.querySelector('.result-count').textContent = `${hits.length}개 용어`;
    });
  }
  return { title: '용어집', html, mount };
}

export function aboutView() {
  const s = stats();
  const html = `
  <header class="page-head">
    <p class="eyebrow">About the data</p>
    <h1 class="page-title">자료 원칙과 출처</h1>
    <p class="page-sub">해부학은 정확성이 중요한 분야입니다. 이 자료집이 어떤 원칙으로 만들어졌는지, 무엇이 아직 검증되지 않았는지 공개합니다.</p>
  </header>
  <section class="prose">
    <h2>검증 상태</h2>
    <ul>${Object.values(REVIEW).map((r) => `<li><strong>${esc(r.label)}</strong> — ${esc(r.text)}</li>`).join('')}</ul>
    <p>현재 등록된 ${s.items}개 항목은 모두 <strong>검토 필요</strong> 상태입니다. 이는곳·닿는곳·신경 지배·기능은 아래 교과서 자료의 일반적 서술을 따랐지만, 해부학 전문가의 검수를 거치지 않았습니다.</p>
    <h2>용어</h2>
    <p>대한해부학회 신용어를 대표 명칭으로 쓰고, 구용어·영어·라틴어(FIPAT Terminologia Anatomica)를 함께 적어 어느 명칭으로든 검색되게 했습니다.</p>
    <h2>이미지</h2>
    <p>시각 자료는 두 종류로 구분해 표시합니다.</p>
    <ul>
      <li><strong>모델 추출 도판</strong> — BodyParts3D 3D 모델의 실제 형상을 정사영으로 직접 렌더링한 그림(<code>tools/make_deltoid_plates.py</code>). 근육별 색 구분, 설명선, 이는곳·닿는곳 영역 표시는 자체 추가했습니다. 이는곳·닿는곳 영역은 모델에서 근육과 뼈 표면이 0.3cm 이내로 맞닿은 부분을 계산한 근사치입니다. 움직임 도판은 위팔뼈만 회전시키고 근육을 작용선으로 표시한 단순화 그림입니다.</li>
      <li><strong>자체 제작 개념 도식</strong> — 관절 각도, 자세, 조직 층의 순서만 단순하게 표현한 그림으로, 근육의 실제 형태를 그린 해부학 일러스트가 아닙니다.</li>
    </ul>
    <p>AI로 생성한 이미지는 사용하지 않았고, 다른 사이트의 이미지·영상도 사용하지 않았습니다. 모든 도판은 ‘검토 필요’ 상태입니다. 검증된 자료가 없는 항목에는 그림 대신 ‘자료 준비 중’을 표시합니다.</p>
    <h2>3D 모델</h2>
    <div class="table-wrap model-status">
      <table class="gloss">
        <thead><tr><th>모델</th><th>파일</th><th>메쉬</th><th>자료 연결</th><th>파일 상태</th></tr></thead>
        <tbody>${db.models3d.models.map((m) => `<tr>
          <td data-l="모델"><strong>${esc(m.title)}</strong><br><small>${esc(m.id)}</small></td>
          <td data-l="파일"><code>${esc(m.url)}</code>${m.fileSize ? `<br><small>${(m.fileSize / 1e6).toFixed(2)} MB · 삼각형 ${(m.triangles || 0).toLocaleString()}</small>` : ''}</td>
          <td data-l="메쉬">${m.meshes.length}${m.mappingError ? ' ⚠ 매핑 파일 오류' : ''}</td>
          <td data-l="자료 연결">${m.meshes.filter((x) => x.anatomyItemId).length} / ${m.meshes.length}</td>
          <td data-l="파일 상태" data-model-status="${esc(m.url)}">확인 중…</td></tr>`).join('')}</tbody>
      </table>
    </div>
    ${db.models3d.models.map((m) => `
      <h3 class="prose-h3">${esc(m.title)}</h3>
      <dl class="license">
        <div><dt>자료명</dt><dd>${esc(m.source.name)}</dd></div>
        <div><dt>원작자</dt><dd>${esc(m.source.author)}</dd></div>
        <div><dt>다운로드 출처</dt><dd><a href="${esc(m.source.url)}" target="_blank" rel="noopener noreferrer">${esc(m.source.url)}</a></dd></div>
        <div><dt>라이선스</dt><dd><a href="${esc(m.source.licenseUrl)}" target="_blank" rel="noopener noreferrer">${esc(m.source.license)}</a></dd></div>
        <div><dt>수정 여부</dt><dd>${esc(m.source.modified)}</dd></div>
        <div><dt>상업적 이용</dt><dd>${esc(m.source.commercialUse)}</dd></div>
        <div><dt>출처 표기</dt><dd>${esc(m.source.attribution)}${m.source.attributionLegacy ? `<br><small>원본 파일 표기: ${esc(m.source.attributionLegacy)}</small>` : ''}</dd></div>
        ${m.source.derivativeLicense ? `<div><dt>파생물</dt><dd>${esc(m.source.derivativeLicense)}</dd></div>` : ''}
        <div><dt>파일</dt><dd><code>${esc(m.url)}</code>${m.fileSize ? ` · ${(m.fileSize / 1e6).toFixed(1)}MB` : ''}${m.triangles ? ` · 삼각형 ${m.triangles.toLocaleString()}개` : ''}</dd></div>
        <div><dt>구조 수</dt><dd>개별 메쉬 ${m.meshes.length}개 · 해부학 자료와 연결 ${m.meshes.filter((x) => x.anatomyItemId).length}개 · 매핑 파일 <code>${esc(m.mapping)}</code> · 검증 상태: 검토 필요</dd></div>
      </dl>
      <ul>${(m.notes || []).map((n) => `<li>${esc(n)}</li>`).join('')}</ul>`).join('')}
    <p>3D 뷰어는 Three.js r170(MIT 라이선스)을 사용하며, 프로젝트 안의 <code>vendor/three</code> 사본을 불러오므로 외부 CDN 없이 동작합니다.</p>
    <h2>3D 동작 시뮬레이션의 범위</h2>
    <p>3D 관찰 탭의 ‘동작’ 패널(관절 동작 ${(db.motions || []).length}종)은 <strong>교육용 단순화 시뮬레이션</strong>입니다. 실제 BodyParts3D 뼈 메쉬를 형상에서 계산한 관절 중심으로 강체 회전·이동하며, 아래는 구현하지 않았습니다.</p>
    <ul>
      <li><strong>근육 변형 없음</strong> — 관절을 가로지르는 근육은 메쉬 대신 이는곳→닿는곳 작용선으로 표시하고, 길이 변화는 작용선 길이로 계산한 추정치입니다.</li>
      <li><strong>수축 상태는 판정 규칙에 따른 추정</strong> — 역할·길이 변화·부하 조건(중력/저항)으로 단축성·편심성·등척성을 표시합니다. 근전도 같은 실측 데이터가 아닙니다.</li>
      <li><strong>관절면 운동학(roll·glide) 계산 없음</strong> — 단계별 텍스트 설명으로만 제공합니다.</li>
      <li><strong>메쉬 없는 근육</strong> — 얼굴근육·씹기근육·배벽 근육·넓은등근 등은 모델에 형상이 없어 3D에서 선택할 수 없습니다. 씹기근육은 가상 작용선(위치 근사)으로만 표시합니다.</li>
      <li>손가락 개별 동작, 갈비뼈 개별 동작, 얼굴 표정 3D는 없습니다.</li>
    </ul>
    <h2>건강 정보</h2>
    <p>이 자료집은 해부학 학습용이며, 통증이나 질환의 진단·치료 정보를 제공하지 않습니다.</p>
    <h2>계정과 기록</h2>
    <p>로그인 기능은 없습니다. 즐겨찾기·학습 기록·메모는 사용 중인 브라우저에만 저장됩니다.</p>
    <h2>참고 자료</h2>
    <ol class="sources">${db.sources.map((src) => `<li>${src.url ? `<a href="${esc(src.url)}" target="_blank" rel="noopener noreferrer">${esc(src.title)}</a>` : esc(src.title)}<span class="src-pub">${esc(src.publisher)}</span>${src.note ? `<span class="src-note">${esc(src.note)}</span>` : ''}</li>`).join('')}</ol>
  </section>`;
  async function mount(root) {
    // 모델별 로딩 상태: 실제 파일에 HEAD 요청
    for (const cell of root.querySelectorAll('[data-model-status]')) {
      try {
        const res = await fetch(cell.dataset.modelStatus, { method: 'HEAD', cache: 'no-cache' });
        const len = Number(res.headers.get('content-length'));
        cell.textContent = res.ok ? `✓ 사용 가능${len ? ` (${(len / 1e6).toFixed(2)} MB)` : ''}` : `✕ 파일 없음 (${res.status})`;
      } catch {
        cell.textContent = '✕ 확인 실패';
      }
    }
  }
  return { title: '자료 원칙', html, mount };
}
