import { Link } from "react-router-dom";

export const LOGO_URL = "https://customer-assets-lxgj4vgw.emergentagent.net/job_72a04638-96a3-4c1c-a91a-c746c65042bb/artifacts/wju9r7vz_image.png";

export function Brand({ compact = false, light = false }: { compact?: boolean; light?: boolean }) {
  return (
    <Link to="/" data-testid={compact ? "brand-compact-link" : "brand-logo-link"} className="group flex items-center gap-3">
      <img src={LOGO_URL} alt="Vidyadwar logo" className={compact ? "h-10 w-10 rounded-xl object-cover object-top" : "h-11 w-11 rounded-xl object-cover object-top"} />
      <span className={`font-heading leading-none tracking-tight ${light ? "text-white" : "text-slate-950"}`}>
        <span className="block text-xl font-extrabold">Vidyadwar</span>
        {!compact && <span className={`mt-1 block text-[9px] font-semibold uppercase tracking-[0.18em] ${light ? "text-teal-200" : "text-teal-700"}`}>Decision Navigator</span>}
      </span>
    </Link>
  );
}