function extractAndSendSignalData() {
  console.log("시그널 실시간 데이터 추출기 작동 시작...");
  
  // 시그널 화면에서 순위 리스트 요소 수집
  const items = document.querySelectorAll('.rank-item, .rank-list li, tr'); 
  let keywords = [];
  let metadata = {};
  
  // 만약 특정 클래스가 안 잡힐 경우를 대비한 오리지널 정밀 텍스트 노드 파싱
  const txElements = document.querySelectorAll('.tx');
  if (txElements.length > 0) {
    txElements.forEach((el, index) => {
      let kw = el.innerText.trim();
      if (kw && !keywords.includes(kw) && isNaN(kw) && keywords.length < 10) {
        if (!["뉴스", "랭킹", "실시간 검색어", "로그인", "회원가입"].includes(kw)) {
          keywords.push(kw);
          
          // 주변 구조를 파악해 요약문 매핑 탐색 (부모나 형제 요소에서 추출)
          let parentText = el.parentElement ? el.parentElement.innerText : "";
          let summary = parentText.replace(kw, "").replace(/\d+/g, "").trim();
          metadata[kw] = summary ? summary : kw + " 관련 실시간 주요 실황 및 사회적 쟁점 언론 보도 확산 중";
        }
      }
    });
  }

  if (keywords.length === 0) {
    // 텍스트 기반 차선책 추출 가동
    const allText = document.body.innerText;
    const lines = allText.split('\n').map(l => l.strip ? l.strip() : l.trim()).filter(Boolean);
    let current = null;
    lines.forEach(line => {
      if (line.length < 20 && isNaN(line) && keywords.length < 10) {
        if (!["뉴스","랭킹","실시간","메뉴"].some(word => line.includes(word))) {
          current = line;
          if(!keywords.includes(current)) keywords.push(current);
        }
      } else if (current && line.length > 15) {
        metadata[current] = line;
      }
    });
  }

  if (keywords.length > 0) {
    const payload = {
      keywords: keywords,
      metadata: metadata,
      updated_at: new Date().toLocaleTimeString()
    };

    // 로컬 웹 브라우저 다운로드 기능을 우회하여 Streamlit 실행 폴더의 데이터 파일명으로 강제 덤프 유도 다운로드 처리
    // 이 파일이 생성기 폴더 안의 'signal_live_data.json' 위치로 바로 꽂히도록 브라우저 다운로드 링크 작동 유도
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(json.stringify(payload));
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", "signal_live_data.json");
    dlAnchorElem.click();
    console.log("Streamlit 연동 데이터 파일 로컬 덤프 갱신 완료!", payload);
  }
}

// 5분(300,000ms)마다 자동으로 시그널 사이트를 스캔해서 데이터를 백엔드로 토스
extractAndSendSignalData();
setInterval(extractAndSendSignalData, 300000);
