// src/plugins/fontawesome.js
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import '../lib/icons.js'; // Import the existing icons setup

export default {
  install: (app) => {
    app.component('FontAwesomeIcon', FontAwesomeIcon);
  }
};
