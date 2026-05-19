# 메인 생성 로직
if st.sidebar.button("✨ 글 생성하기", type="primary"):
    if not api_key:
        st.error("API 키를 입력하세요.")
    elif query == "대기 중..." or not query:
        st.error("작성할 키워드를 선택해주세요.")
    else:
        factual_summary = live_metadata.get(query, "최신 정보 없음")
        
        for p in platforms:
            # 1. 스타일에 따른 톤앤매너 지정
            tone_instruction = ""
            if style == "📰 뉴스 보도체":
                tone_instruction = "신뢰감 있고 객관적인 신문 기사 어조(~다, ~합니다)로 작성하세요. 자극적인 수식어는 배제하고 팩트 전달에 집중하세요."
            elif style == "😊 쉬운 설명체":
                tone_instruction = "친근한 블로그 어조(~에요, ~습니다)로 작성하세요. 독자가 이해하기 쉽게 비유를 섞어가며 친절하게 설명하세요. 적절한 이모지를 섞어주면 좋습니다."

            # 2. 플랫폼별 특성 반영 (네이버 vs 티스토리)
            platform_instruction = ""
            if p == "네이버 블로그":
                platform_instruction = (
                    "- 제목은 클릭을 부르는 매력적인 제목 3개를 추천해 주되, 그중 가장 좋은 것 하나를 본문 맨 위에 크게 배치하세요.\n"
                    "- 네이버 블로그 특성에 맞게 '서론-본문(소제목 분할)-결론(내 의견/맺음말)' 구조를 명확히 하세요.\n"
                    "- 가독성을 위해 문단을 자주 나누고, 중요한 키워드는 문맥 속에서 자연스럽게 강조되도록 하세요."
                )
            elif p == "티스토리":
                platform_instruction = (
                    "- SEO(검색엔진 최적화)에 최적화된 구글 친화적 구조로 작성하세요.\n"
                    "- 제목은 핵심 키워드가 맨 앞에 오는 명확한 제목 1개만 깔끔하게 작성하세요.\n"
                    "- 본문은 H2, H3 형태의 논리적인 소제목 구조를 갖추고, 정보의 깊이가 느껴지도록 서술하세요."
                )

            # 3. 종합 시스템 프롬프트 조립
            sys_prompt = (
                f"당신은 전문 파워블로거이자 카피라이터입니다. 제공된 요약 정보를 바탕으로 독자에게 유익하고 완성도 높은 글을 작성해야 합니다.\n\n"
                f"[톤앤매너 규칙]\n{tone_instruction}\n\n"
                f"[플랫폼별 작성 규칙]\n{platform_instruction}\n\n"
                f"[⚠️ 절대 금지 규칙]\n"
                f"- 본문 내에서 마크다운 강조 기호인 '**' (별표 두 개)는 절대 사용하지 마세요. (텍스트 강조 시 기호 없이 문맥으로 처리할 것)\n"
                f"- AI가 작성한 티가 나는 문구(예: 'AI 요약에 따르면', '아래는 요약 내용입니다')는 절대 넣지 마세요. 직접 취재하고 분석한 글처럼 써야 합니다.\n"
                f"- 분량은 최소 공백 제외 1,500자 이상의 풍부한 정보량으로 채워주세요."
            )
            
            # 4. 사용자 메시지
            user_msg = (
                f"● 타겟 키워드: {query}\n"
                f"● 팩트 및 정보 요약:\n{factual_summary}\n\n"
                f"위 정보를 완벽히 녹여내어 독자들이 끝까지 읽을 수 있는 매력적인 블로그 포스팅을 완성해줘."
            )
            
            with st.spinner(f"[{p}] {style} 스타일로 글을 생성하는 중..."):
                try:
                    content = call_ai_prime_tech(api_key, sys_prompt, user_msg, model)
                    
                    # 화면 출력 구조 개선
                    st.success(f"✅ {p} 생성 완료!")
                    st.subheader(f"✨ {p} 결과물 ({style})")
                    
                    # 복사하기 편하도록 텍스트 영역 제공
                    st.text_area(f"{p} 본문 (복사용)", value=content, height=600, key=f"txt_{p}")
                    
                    # 히스토리 저장
                    save_to_history(query, p, content)
                    st.divider()
                except Exception as e:
                    st.error(f"{p} 생성 중 오류가 발생했습니다: {str(e)}")
