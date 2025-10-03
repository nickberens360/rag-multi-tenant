import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import {
  // Navigation & Core
  mdiHome, mdiViewDashboard, mdiMagnify, mdiChartLine, mdiFileDocument,
  mdiAccountGroup, mdiAccount, mdiAccountDetails, mdiMenu, mdiClose, mdiRefresh, mdiExport,

  // Actions & Controls
  mdiLock, mdiLockOutline, mdiLockCheck, mdiLogout, mdiFilter, mdiEye,
  mdiDownload, mdiUpload, mdiCloudUpload, mdiPaperclip, mdiDelete,
  mdiPencil, mdiNoteEdit, mdiUndo, mdiChevronLeft, mdiChevronRight, mdiChevronDown,
  mdiChevronUp,
  mdiContentSave, mdiFormatTextVariant, mdiMapMarker, mdiText, mdiFile,
  mdiPlus, mdiDragVertical, mdiEyeOff, mdiArrowUp, mdiArrowDown, mdiDotsVertical,
  mdiToggleSwitch, mdiSort, mdiCheckboxMarked, mdiArrowRight, mdiDeleteForever,
  mdiTag, mdiTagOutline, mdiClipboardList, mdiAlertOctagon, mdiReply, mdiRoad,
  mdiFlag, mdiCached, mdiMessageText, mdiKey, mdiImport, mdiShieldCheck, mdiAlertCircle,
  mdiRobot, mdiGoogle, mdiDatabase, mdiTimer, mdiFingerprint, mdiBookOpen,
  mdiSpeedometer, mdiGauge, mdiIpNetwork, mdiCheckCircleOutline, mdiShield,

  // User Management Icons
  mdiAccountPlus, mdiAccountOff, mdiAccountCheck, mdiAccountRemove, mdiEmail, mdiShieldAccount,
  mdiCloseCircle, mdiAccountHeart,

  // Settings Navigation Icons
  mdiCogBox, mdiMagnifyScan,

  // Missing Icons - Adding these to fix Vue warnings
  mdiMessageQuestion, mdiFeatureSearch, mdiWrench, mdiSourceBranch,
  mdiTextLong, mdiLinkVariant, mdiFormatListNumbered, mdiLanguageMarkdown,
  mdiEyeOutline, mdiCodeTags,

  // Status & Feedback
  mdiAlert, mdiCheck, mdiCheckCircle, mdiClockOutline, mdiTrendingUp,
  mdiTrendingDown, mdiThumbUpOutline, mdiThumbUp, mdiThumbDown,
  mdiAlertCircleOutline, mdiBell,

  // Content & Knowledge
  mdiBookOpenPageVariant, mdiInformation, mdiFolder, mdiFormatListBulleted,
  mdiCodeBraces, mdiFilePdfBox, mdiFileDocumentOutline, mdiTextBox, mdiWeb, mdiHelpCircleOutline, mdiCog,
  mdiBrain, mdiTune, mdiTarget, mdiNumeric, mdiFormatListGroup, mdiPalette,

  // Theme & System
  mdiWeatherNight, mdiWhiteBalanceSunny, mdiMemory, mdiChartBar,
  mdiLightbulbOutline, mdiLightbulb, mdiTableLarge, mdiTestTube,
  
  // New RAG Settings Icons
  mdiDeveloperBoard,
  // Auto-generate
  mdiAutoFix
} from '@mdi/js'

// Import Vuetify styles
import 'vuetify/styles'

// Theme configurations - Modern LMS colors
const themes = {
  light: {
    dark: false,
    colors: {
      primary: '#6366F1', // Modern indigo
      secondary: '#64748B', // Slate gray
      accent: '#8B78FF', // Light purple accent
      error: '#EF4444', // Modern red
      info: '#3B82F6', // Blue
      success: '#10B981', // Modern green
      warning: '#F59E0B', // Modern amber
      surface: '#FFFFFF',
      background: '#F8FAFC' // Very light gray background
    }
  },
  dark: {
    dark: true,
    colors: {
      primary: '#8B78FF', // Lighter purple for dark mode
      secondary: '#6B7280', // Medium gray
      accent: '#A78BFA', // Light violet accent
      error: '#F87171', // Lighter red
      info: '#60A5FA', // Lighter blue
      success: '#34D399', // Lighter green
      warning: '#FBBF24', // Lighter amber
      surface: '#0e0e0e', // Very dark surface for cards
      background: '#000000' // Black background
    }
  }
}

// Modern typography for LMS design
const typography = {
  fontFamily: '"Roboto", -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif'
}

// Icon aliases configuration
const iconAliases = {
  // Navigation
  home: mdiHome,
  dashboard: mdiViewDashboard,
  search: mdiMagnify,
  chart: mdiChartLine,
  document: mdiFileDocument,
  users: mdiAccountGroup,
  knowledge: mdiBookOpenPageVariant,

  // Actions
  menu: mdiMenu,
  close: mdiClose,
  refresh: mdiRefresh,
  export: mdiExport,
  filter: mdiFilter,
  view: mdiEye,
  eye: mdiEye,
  download: mdiDownload,
  upload: mdiUpload,
  'cloud_upload': mdiCloudUpload,
  'attach_file': mdiPaperclip,
  delete: mdiDelete,
  'delete-forever': mdiDeleteForever,
  edit: mdiPencil,
  'note-edit': mdiNoteEdit,
  undo: mdiUndo,
  'chevron-left': mdiChevronLeft,
  'chevron-right': mdiChevronRight,
  'chevron-down': mdiChevronDown,
  'chevron-up': mdiChevronUp,
  save: mdiContentSave,
  'format-text': mdiFormatTextVariant,
  'map-marker': mdiMapMarker,
  text: mdiText,
  file: mdiFile,
  plus: mdiPlus,
  'drag-vertical': mdiDragVertical,
  'eye-off': mdiEyeOff,
  'arrow-up': mdiArrowUp,
  'arrow-down': mdiArrowDown,
  'arrow-right': mdiArrowRight,
  'dots-vertical': mdiDotsVertical,
  'alert-triangle': mdiAlert,
  'toggle-switch': mdiToggleSwitch,
  'sort': mdiSort,
  'checkbox-marked': mdiCheckboxMarked,
  'trending-up': mdiTrendingUp,
  tag: mdiTag,
  'tag-outline': mdiTagOutline,
  cog: mdiCog,
  'clipboard-list': mdiClipboardList,
  'alert-octagon': mdiAlertOctagon,
  'format-list-bulleted': mdiFormatListBulleted,
  'message-reply': mdiReply,
  'message-text': mdiMessageText,
  route: mdiRoad,
  'feature-flag': mdiFlag,
  cached: mdiCached,
  key: mdiKey,
  import: mdiImport,
  'shield-check': mdiShieldCheck,
  'alert-circle': mdiAlertCircle,
  robot: mdiRobot,
  google: mdiGoogle,
  database: mdiDatabase,
  timer: mdiTimer,
  'clock-outline': mdiClockOutline,
  fingerprint: mdiFingerprint,
  'book-open': mdiBookOpen,
  speedometer: mdiSpeedometer,
  gauge: mdiGauge,
  'ip-network': mdiIpNetwork,
  'check-circle-outline': mdiCheckCircleOutline,

  // User Management
  'account-plus': mdiAccountPlus,
  'account-off': mdiAccountOff,
  'account-remove': mdiAccountRemove,
  'account-check': mdiAccountCheck,
  'account-details': mdiAccountDetails,
  'account-group': mdiAccountGroup,
  email: mdiEmail,
  'shield-account': mdiShieldAccount,
  'close-circle': mdiCloseCircle,

  // Status
  alert: mdiAlert,
  check: mdiCheck,
  'check-circle': mdiCheckCircle,
  'check_circle': mdiCheckCircle,
  clock: mdiClockOutline,
  schedule: mdiClockOutline,
  trendUp: mdiTrendingUp,
  trendDown: mdiTrendingDown,
  'thumb-up-outline': mdiThumbUpOutline,
  'thumb-up': mdiThumbUp,
  'thumb-down': mdiThumbDown,
  warning: mdiAlertCircleOutline,
  bell: mdiBell,

  // Content types
  info: mdiInformation,
  information: mdiInformation,
  folder: mdiFolder,
  'list-bulleted': mdiFormatListBulleted,
  description: mdiFileDocument,
  'data_object': mdiCodeBraces,
  'picture_as_pdf': mdiFilePdfBox,
  'text_snippet': mdiTextBox,
  language: mdiWeb,
  web: mdiWeb,
  article: mdiFileDocumentOutline,
  'insert_drive_file': mdiFileDocumentOutline,
  help: mdiHelpCircleOutline,
  'help-circle': mdiHelpCircleOutline,
  'help-circle-outline': mdiHelpCircleOutline,
  settings: mdiCog,
  brain: mdiBrain,
  tune: mdiTune,
  target: mdiTarget,
  numeric: mdiNumeric,
  pencil: mdiPencil,
  'format-list-group': mdiFormatListGroup,
  palette: mdiPalette,
  code: mdiCodeBraces,
  test: mdiTestTube,

  // User & Security
  account: mdiAccount,
  lock: mdiLock,
  'lock-outline': mdiLockOutline,
  'lock-check': mdiLockCheck,
  logout: mdiLogout,

  // Theme
  'weather-night': mdiWeatherNight,
  'light-mode': mdiWhiteBalanceSunny,

  // System
  memory: mdiMemory,
  'bar_chart': mdiChartBar,
  lightbulb: mdiLightbulbOutline,
  recommend: mdiLightbulb,
  table: mdiTableLarge,

  // RAG Settings Icons (using existing imports)
  image: mdiFileDocument,
  map: mdiMapMarker,
  bug: mdiAlert,
  storage: mdiDatabase,
  'developer-mode': mdiDeveloperBoard,
  construction: mdiCog,
  speed: mdiGauge,
  api: mdiCog,
  diversity: mdiTune,
  'format-header': mdiFormatTextVariant,
  'database-search': mdiMagnify,
  'folder-search': mdiFolder,

  // Settings Navigation Icons
  'cog-box': mdiCogBox,
  'magnify-scan': mdiMagnifyScan,
  'account-heart': mdiAccountHeart,

  // Missing icon aliases - fix for Vue warnings
  'message-question': mdiMessageQuestion,
  'feature-search': mdiFeatureSearch,
  'wrench': mdiWrench,
  'source-branch': mdiSourceBranch,
  'text-long': mdiTextLong,
  'link-variant': mdiLinkVariant,
  'format-list': mdiFormatListNumbered,
  'markdown': mdiLanguageMarkdown,
  'code-braces': mdiCodeBraces,
  'chart-line': mdiChartLine,
  'shield': mdiShield,
  'preview': mdiEyeOutline,
  // Auto-generate taxonomy
  'auto-generate': mdiAutoFix
}

export default createVuetify({
  theme: {
    defaultTheme: 'dark',
    themes,
    variations: {
      colors: ['primary', 'secondary', 'accent', 'error', 'info', 'success', 'warning'],
      lighten: 5,
      darken: 5
    }
  },
  typography,
  icons: {
    defaultSet: 'mdi',
    aliases: {
      ...aliases,
      ...iconAliases
    },
    sets: { mdi }
  },
  defaults: {
    VCard: {
      elevation: 1,
      rounded: 'lg'
    },
    VSnackbar: {
      scrim: false,
      contained: true,
      retainFocus: false,
      closeOnBack: false
    },
    VBtn: {
      variant: 'flat',
      rounded: 'lg'
    },
    VDataTable: {
      itemsPerPage: 25,
      hover: true
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable'
    },
    VSelect: {
      variant: 'outlined',
      density: 'comfortable'
    },
    VDialog: {
      scrim: true,
      'no-click-animation': false,
      transition: 'dialog-transition'
    },
    VOverlay: {
      scrim: true,
      opacity: 0.65
    },
    // Remove custom typography classes since global font handles everything
  }
})
