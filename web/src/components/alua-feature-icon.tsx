type AluaFeatureIconProps = {
  variant: 'gift' | 'lightning' | 'sparkle';
  className?: string;
};

/** Alua Signature: decorative vectors, paired with a visible feature heading. */
export function AluaFeatureIcon({variant, className}: AluaFeatureIconProps) {
  return <svg className={className} viewBox="0 0 80 80" width="80" height="80" fill="none" stroke="#14664F" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {variant === 'gift' ? <>
      <path d="M23 38H57C62 38 65 41 65 46V64C65 69 62 72 57 72H23C18 72 15 69 15 64V46C15 41 18 38 23 38Z"/>
      <path d="M14 26H66C69 26 71 28 71 31V38H9V31C9 28 11 26 14 26ZM40 26V72"/>
      <path d="M40 25C33 25 20 23 20 16C20 8 30 8 34 15L40 25ZM40 25C47 25 60 23 60 16C60 8 50 8 46 15L40 25Z"/>
      <path d="M55 49V59" stroke="#D2A743"/>
    </> : variant === 'lightning' ? <>
      <path d="M47 7L18 44H40L32 73L64 32H44L47 7Z"/>
      <path d="M58 12L65 7M67 20H74" stroke="#D2A743"/>
    </> : <>
      <path d="M35 9C31 28 24 34 6 39C24 44 31 51 35 71C39 51 46 44 64 39C46 34 39 28 35 9Z"/>
      <path d="M66 8L68.5 15.5L76 18L68.5 20.5L66 28L63.5 20.5L56 18L63.5 15.5Z" fill="#D2A743" stroke="none"/>
      <circle cx="67" cy="64" r="3" fill="#14664F" stroke="none"/>
    </>}
  </svg>;
}
