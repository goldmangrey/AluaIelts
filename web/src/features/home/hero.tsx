import {AluaFeatureIcon} from '@/components/alua-feature-icon';
import {LuaMascot} from '@/components/lua-mascot';
import {AIQuestion} from './typewriter';
import s from './hero.module.css';

function BenefitIcon({kind}:{kind:'gift'|'lightning'|'sparkle'}){
  return <span className={s.iconBox}><AluaFeatureIcon variant={kind} className={s.icon}/></span>;
}

function SpeechBubble(){
  return <div className={s.bubble}>
    <svg className={`${s.bubbleShape} ${s.desktopShape}`} viewBox="0 0 1200 440" preserveAspectRatio="none" aria-hidden="true" focusable="false">
      <path d="M154 32C217 12 295 23 375 17C463 10 489 46 584 36C698 24 763 17 862 29C972 41 1035 61 1069 113C1095 151 1088 183 1120 207C1143 226 1169 227 1191 230C1174 247 1142 255 1114 262C1076 270 1090 295 1057 334C1010 391 916 421 820 410C709 398 669 430 557 421C447 412 403 397 320 412C212 431 98 408 56 358C-9 286 20 208 57 146C87 97 97 54 154 32Z"/>
    </svg>
    <svg className={`${s.bubbleShape} ${s.mobileShape}`} viewBox="0 0 360 290" preserveAspectRatio="none" aria-hidden="true" focusable="false">
      <path d="M60 12C102 2 135 13 179 8C224 2 275 5 310 25C344 44 350 80 348 122C346 168 347 201 321 223C304 238 273 239 257 249C242 257 237 270 226 280C225 263 226 252 215 246C208 241 201 243 194 243C151 242 125 233 90 240C47 246 17 228 9 192C0 156 14 128 12 97C10 57 24 23 60 12Z"/>
    </svg>
    <svg className={s.greenRays} viewBox="0 0 64 56" fill="none" stroke="currentColor" strokeWidth="7" strokeLinecap="round" aria-hidden="true"><path d="m7 36 16 6M27 13l11 15M52 4l1 20"/></svg>
    <div className={s.copy}>
      <p className={s.greeting}>Hi, I&apos;m Lua! <span aria-hidden="true">👋</span></p>
      <h1 id="home-title" className={s.title}>Let&apos;s make IELTS <span className={s.underlined}>a little easier.<svg viewBox="0 0 300 18" preserveAspectRatio="none" aria-hidden="true"><path d="M5 12C71 2 177 3 294 12"/></svg></span></h1>
      <p className={s.subtitle}>Choose a skill below. I&apos;ll help you understand your mistakes, one question at a time.</p>
    </div>
  </div>;
}

export function HomeHero(){
  return <section className={s.hero} aria-labelledby="home-title">
    <div className={s.composition}>
      <SpeechBubble/>
      <div className={s.lua} data-lua-context="hero">
        <svg className={s.yellowRays} viewBox="0 0 58 54" fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="round" aria-hidden="true"><path d="m5 42 14 1M16 20l12 11M39 6l3 18"/></svg>
        <LuaMascot mode="idle" size={410} priority/>
      </div>
    </div>
    <div className={s.benefits}>
      <div className={s.benefit}><BenefitIcon kind="gift"/><div><h2>Free forever</h2><p>No trial expiry</p></div></div>
      <div className={s.benefit}><BenefitIcon kind="lightning"/><div><h2>Instant results</h2><p>See your score right away</p></div></div>
      <div className={s.benefit}><BenefitIcon kind="sparkle"/><div><h2>AI explanations</h2><AIQuestion/></div></div>
    </div>
  </section>;
}
