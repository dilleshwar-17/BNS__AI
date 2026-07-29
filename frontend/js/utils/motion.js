(function () {
  const Motion = {
    init() {
      this.navbarScroll()
      this.scrollReveal()
      this.cardMouseGlow()
    },

    navbarScroll() {
      const nav = document.getElementById('navbar')
      if (!nav) return

      const check = () => {
        nav.classList.toggle('scrolled', window.scrollY > 20)
      }

      check()
      let ticking = false
      window.addEventListener('scroll', () => {
        if (!ticking) {
          requestAnimationFrame(() => {
            check()
            ticking = false
          })
          ticking = true
        }
      })
    },

    scrollReveal() {
      if (!window.IntersectionObserver) return

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add('visible')
              observer.unobserve(entry.target)
            }
          })
        },
        { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
      )

      document.querySelectorAll(
        '.reveal, .reveal-left, .reveal-right, .reveal-scale'
      ).forEach((el) => observer.observe(el))
    },

    cardMouseGlow() {
      document.querySelectorAll('.draft-card, .feature-card, .stat-card').forEach((card) => {
        card.addEventListener('mousemove', (e) => {
          const rect = card.getBoundingClientRect()
          const x = ((e.clientX - rect.left) / rect.width) * 100
          const y = ((e.clientY - rect.top) / rect.height) * 100
          card.style.setProperty('--mx', `${x}%`)
          card.style.setProperty('--my', `${y}%`)
        })
      })
    },
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => Motion.init())
  } else {
    Motion.init()
  }

  window.Motion = Motion
})()
