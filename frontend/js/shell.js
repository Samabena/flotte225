/* Shared sidebar behavior: desktop collapse (persisted) + mobile drawer.
   Replaces the per-page IIFE that was duplicated at the bottom of each page. */
(function () {
  var s = document.getElementById('sidebar');
  var t = document.getElementById('sidebar-toggle');
  var mb = document.getElementById('mobile-menu-btn');
  var bd = document.getElementById('sidebar-backdrop');
  if (!s) return;

  if (localStorage.getItem('flotte225-sidebar-collapsed') === 'true') {
    s.classList.add('collapsed');
  }
  if (t) {
    t.addEventListener('click', function () {
      s.classList.toggle('collapsed');
      localStorage.setItem(
        'flotte225-sidebar-collapsed',
        s.classList.contains('collapsed')
      );
    });
  }
  if (mb && bd) {
    mb.addEventListener('click', function () {
      s.classList.add('mobile-open');
      bd.classList.add('show');
    });
    bd.addEventListener('click', function () {
      s.classList.remove('mobile-open');
      bd.classList.remove('show');
    });
  }
})();
