const CATEGORY_META: Record<string, { color: string; icon: string }> = {
    'Sub-GHz':   { color: '#A5F4BE', icon: 'sub-ghz.svg' },
    'RFID':      { color: '#FFF493', icon: 'rfid.svg' },
    'NFC':       { color: '#98CEFE', icon: 'nfc.svg' },
    'Infrared':  { color: '#FE938C', icon: 'infrared.svg' },
    'GPIO':      { color: '#A7F2EA', icon: 'gpio.svg' },
    'iButton':   { color: '#E1BBA6', icon: 'ibutton.svg' },
    'USB':       { color: '#FFBEE9', icon: 'usb.svg' },
    'Games':     { color: '#FFC486', icon: 'games.svg' },
    'Media':     { color: '#DFB5FF', icon: 'media.svg' },
    'Tools':     { color: '#DFF159', icon: 'tools.svg' },
    'Bluetooth': { color: '#8BACFF', icon: 'bluetooth.svg' }
  };


export const categoryColor = (name: string) => CATEGORY_META[name]?.color ?? '#EBEBEB';
export const categoryIcon  = (name: string) => CATEGORY_META[name]?.icon ?? null;
