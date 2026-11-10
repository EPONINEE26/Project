// 화면 HTML은 Django 템플릿에서 만듭니다.
// JavaScript는 필터 선택 시 GET 폼을 제출하는 보조 기능만 담당합니다.
document.addEventListener('change', function (event) {
    const form = event.target.closest('#filter-form, .year-form');
    if (form && event.target.matches('select, input[type="radio"]')) {
        form.requestSubmit();
    }
});
