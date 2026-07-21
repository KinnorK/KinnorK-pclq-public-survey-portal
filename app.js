(function () {
  const form = document.getElementById('surveyForm');
  const bar = document.getElementById('progressBar');
  if (form && bar) {
    const update = () => {
      const groups = new Set();
      let complete = 0;
      let total = 0;
      form.querySelectorAll('[required]').forEach((el) => {
        if (el.type === 'radio') {
          if (groups.has(el.name)) return;
          groups.add(el.name);
          total += 1;
          if (form.querySelector(`input[name="${CSS.escape(el.name)}"]:checked`)) complete += 1;
        } else if (el.type === 'checkbox') {
          total += 1;
          if (el.checked) complete += 1;
        } else {
          total += 1;
          if (String(el.value || '').trim()) complete += 1;
        }
      });
      bar.style.width = `${total ? Math.round(complete / total * 100) : 0}%`;
    };
    form.addEventListener('change', update);
    form.addEventListener('input', update);
    update();
  }
})();

function copySurveyUrl() {
  const field = document.getElementById('surveyUrl');
  if (!field) return;
  navigator.clipboard.writeText(field.value).then(() => {
    const original = field.value;
    field.value = 'Copied to clipboard';
    setTimeout(() => { field.value = original; }, 1200);
  });
}
