# 젤다의 전설 4개의 검 25주년 에디션 한글 패치

*The Legend of Zelda: Four Swords Anniversary Edition* (DSiWare, 북미판 `KQ9E`) 비공식 한국어 팬 패치입니다.
대사는 일본어판 원문을 기준으로 번역했습니다.

**제작: arqhive**

- 대사·안내문·시스템 메시지 한글화 (215 / 220 항목, 스태프 롤 제외)
- 한글 글리프가 추가된 폰트
- 주요 메뉴·타이틀·스테이지 이름판 그래픽 한글화
- 이전 버전 실기 확인: 한국판 3DS(CFW) + TWiLight Menu++
- v1.1 그래픽 수정본: 사용자 에뮬레이터 실행 확인 완료

> 이 저장소에는 **게임 데이터(롬, 추출한 원문 대사, 그래픽, 스크린샷)가 들어 있지 않습니다.**
> 패치를 만들거나 적용하려면 본인이 소유한 게임에서 직접 덤프한 원본이 필요합니다.

## 사용자용: 패치 적용

현재 버전은 **v1.1**입니다. [GitHub Release](https://github.com/arqhive/zelda-four-swords-anniversary-edition-kor-patch/releases/tag/v1.1)의 ZIP(패치 + 설명서) 또는 [`release/`의 BPS](release/Zelda_4Swords_AE_KQ9E_Korean_v1.1.bps)를 사용하세요. 적용 방법은 [`README_한국어.txt`](release/README_한국어.txt)를 참고하세요.

v1.1은 게임 제목 로고, 파일 복사·삭제 안내, 공통 버튼·대기 표시·색 선택 변형, 멀티플레이 메뉴를 한글화하고 수련장 지도 이름판의 영문 잔여 픽셀을 제거했습니다. 대사와 폰트는 v1.0.1 그대로입니다. **이전 한글 패치본이 아닌 북미판 원본에 적용하는 누적 패치**입니다.

| 원본 (북미판 DSiWare, 복호화) | 값 |
|---|---|
| 크기 | 14,496,768 바이트 |
| CRC32 | `0EEE2777` |
| SHA1 | `e0a0086df319f4a921111083fbea18a66527a801` |

| 패치 적용 결과 | 값 |
|---|---|
| CRC32 | `35B6673B` |
| SHA1 | `cb6fd42ca284e958d53c48640aa8bc087635ba2a` |

실행은 TWiLight Menu++(게임 언어 English) 또는 Unlaunch 환경에서 해야 합니다. 자세한 내용은 사용자용 설명서를 보세요.

- **3DS / DSi 실기**: TWiLight Menu++ 에서 실행
- **melonDS**: DSi 모드(Full BIOS Boot 끔) + 에뮬 NAND에 Unlaunch 설치 → Manage DSi titles 로 패치된 롬과 TMD를 Import → Boot firmware 중 A+B → Unlaunch 메뉴에서 실행.
  롬을 직접 열거나 TWiLight Menu++로 실행하면 흰 화면이 됩니다. 단계별 방법은 [사용자 설명서](release/README_한국어.txt)에 있습니다.

## 개발자용: 직접 빌드

### 요구 사항
- Python 3.10 이상, [Pillow](https://pypi.org/project/pillow/)
- Windows의 **굴림(`gulim.ttc`)** 폰트 — 한글 글리프를 이 폰트로 렌더링합니다.
  다른 환경/폰트 버전에서는 결과 해시가 달라질 수 있습니다.
- 원본 롬 (위 해시와 일치하는 파일)

### 빌드
```bash
python tools/build_ko.py --rom path/to/00000000 --out work/KQ9E_ko.nds
python tools/bps.py create path/to/00000000 work/KQ9E_ko.nds work/patch.bps
```

`build_ko.py`는 다음을 수행합니다.
1. `translation/ko.json`의 한국어 대사를 `us.kmsg` 영어 칸에 넣기
2. 필요한 한글 글리프를 `font_ltn.nftr`에 추가
3. `patches/gfx/*.bps`로 메뉴·이름판·로고 그래픽 파일(`subtask_us_en.cmp`, `zeldat_us_en.bin`, `subtask.cmp`) 교체
4. 사용하지 않는 `all.kmsg`를 비워 공간 확보, 파일 재배치
5. DSi 다이제스트(해시 테이블) 재계산

위 결과 해시는 배포 BPS를 적용한 롬 기준입니다. 소스 빌드는 파일 재배치·빈 공간의 이전 데이터 및 폰트 환경에 따라 전체 롬 해시가 달라질 수 있습니다. v1.1에서는 소스 빌드와 배포본의 모든 NitroFS 파일 내용이 같은지 별도로 검증했습니다. 로고 원본 이미지를 별도로 준비하거나 ImageGen을 실행할 필요는 없습니다.

### 번역 작업
```bash
python tools/export_script.py --rom path/to/00000000   # work/translation/script.json (원문, 커밋 금지)
```
`translation/ko.json`은 `{"항목번호": "한국어 markup"}` 형식입니다.
제어 코드는 `{br}`(줄바꿈), `{wait:N}`, `{c2:N}` 같은 태그로 표기하며 원문의 태그를 유지해야 합니다.
용어는 [`translation/glossary.md`](translation/glossary.md)를 따릅니다.

## 폴더 구조

```
release/          배포용 BPS 패치 + 사용자 설명서
translation/      한국어 번역(ko.json), 용어집
patches/gfx/      한글 그래픽 파일용 BPS 패치
tools/            빌드 도구 (NitroFS, KMSG, NFTR, LZ11/BLZ, BPS, 다이제스트)
tools/dev/        그래픽 한글화에 쓴 개발용 도구 (스크린샷·추출 데이터가 필요, 참고용)
docs/             기술 문서
```

## 기술 문서

파일 형식, 무결성 검사 우회, 압축기 주의점, 그래픽 작업 방법은 [`docs/TECHNICAL.md`](docs/TECHNICAL.md)에 정리했습니다.

## 알려진 문제

- `PRESS A`, `YOU` 그래픽은 영문으로 유지
- 스태프 롤, 게임 내 도움말 페이지는 원문
- 시작의 사당 외 스테이지 이름판은 원래 게임 화면 없이 추정 제작되었으며, 모든 해금 상태·멀티플레이 화면에 대한 전수 검증은 하지 않음

변경 범위와 검증 내역은 [v1.1 릴리즈 노트](docs/RELEASE_v1.1.md)를 참고하세요.

## 라이선스

이 저장소의 도구 코드, 한국어 번역문, 문서는 [MIT License](LICENSE)로 공개합니다 (© 2026 arqhive).
라이선스는 이 프로젝트에서 직접 만든 부분에만 적용되며, 게임 자체와 그 데이터에는 적용되지 않습니다.

## 면책

비공식 팬 번역이며 Nintendo 및 GREZZO와 관련이 없습니다. 「젤다의 전설」 관련 상표·저작권은 Nintendo에 있습니다.
패치된 롬의 배포를 금지합니다.
