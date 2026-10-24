function debounce(fn, wait, options = {}) {
  let timer = null;
  let pendingArgs = null;
  let pendingThis = null;

  function flush() {
    timer = null;
    if (pendingArgs) {
      const args = pendingArgs, self = pendingThis;
      pendingArgs = pendingThis = null;
      fn.apply(self, args);
    }
  }

  function debounced(...args) {
    const isBurstStart = timer === null;
    if (isBurstStart && options.leading) {
      fn.apply(this, args);
    } else {
      pendingArgs = args;
      pendingThis = this;
    }
    clearTimeout(timer);
    timer = setTimeout(flush, wait);
  }

  debounced.cancel = () => {
    clearTimeout(timer);
    timer = null;
    pendingArgs = pendingThis = null;
  };
  return debounced;
}

module.exports = debounce;
