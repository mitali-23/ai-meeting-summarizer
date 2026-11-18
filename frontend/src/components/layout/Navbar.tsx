import { Link, useLocation } from "react-router-dom"
import { Sun, Moon, Settings, Radio } from "lucide-react"
import { useTheme } from "@/lib/theme"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

export function Navbar() {
  const { theme, toggle } = useTheme()
  const location = useLocation()

  return (
    <nav className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3.5">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Radio className="h-4 w-4" />
          </span>
          <span className="font-bold tracking-tight">Signal</span>
        </Link>

        <div className="flex items-center gap-1">
          <Link to="/">
            <Button variant={location.pathname === "/" ? "outline" : "ghost"} size="sm" className="text-sm">
              Summarize
            </Button>
          </Link>
          <Link to="/history">
            <Button variant={location.pathname === "/history" ? "outline" : "ghost"} size="sm" className="text-sm">
              History
            </Button>
          </Link>
          <Button
            variant="outline"
            size="icon"
            className="ml-1"
            onClick={() => toast("Settings are coming soon")}
            aria-label="Settings"
          >
            <Settings className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={toggle} aria-label="Toggle theme">
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </nav>
  )
}
