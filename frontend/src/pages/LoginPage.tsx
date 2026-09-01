import { useState, useEffect } from "react"
import type { FormEvent } from "react"
import { Navigate, useNavigate } from "react-router-dom"
import { Lock, Mail, Sparkles, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/lib/auth"

type Mode = "signin" | "signup"

export function LoginPage() {
  const { session, signIn, signUp } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>("signin")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [toast, setToast] = useState<{ show: boolean; message: string }>({
    show: false,
    message: "",
  })

  useEffect(() => {
    if (toast.show) {
      const timer = setTimeout(() => {
        setToast({ show: false, message: "" })
      }, 4000)
      return () => clearTimeout(timer)
    }
  }, [toast.show])

  if (session) {
    return <Navigate to="/" replace />
  }

  function switchMode(next: Mode) {
    setMode(next)
    setError(null)
    setNotice(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    setNotice(null)
    try {
      if (mode === "signin") {
        await signIn(email, password)
        navigate("/", { replace: true })
      } else {
        const { needsEmailConfirmation } = await signUp(email, password)
        if (needsEmailConfirmation) {
          setMode("signin")
          setNotice("Check your email to confirm your account, then sign in.")
        } else {
          navigate("/", { replace: true })
        }
      }
    } catch (err) {
      if (mode === "signup") {
        setToast({
          show: true,
          message: "Please confirm with the internal team to create your account",
        })
      } else {
        setError(err instanceof Error ? err.message : "Something went wrong")
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4 select-none">
      {toast.show && (
        <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top-2 fade-in-0 max-w-sm">
          <div className="rounded-lg border border-border bg-muted/90 p-3 shadow-lg flex items-start gap-2">
            <span className="text-xs text-foreground">
              {toast.message}
            </span>
            <button
              type="button"
              onClick={() => setToast({ show: false, message: "" })}
              className="shrink-0 text-muted-foreground hover:text-foreground cursor-pointer"
            >
              <X className="size-3" />
            </button>
          </div>
        </div>
      )}

      <div className="w-full max-w-sm space-y-4">
        {/* Branding */}
        <div className="flex flex-col items-center text-center space-y-2 mb-2">
          <div className="flex size-10 items-center justify-center rounded-xl bg-foreground text-background shadow-xs">
            <Sparkles className="size-5" />
          </div>
          <h2 className="text-base font-bold tracking-tight text-foreground">
            Document Copilot
          </h2>
          <p className="text-xs text-muted-foreground">
            SEC Filing Research Assistant
          </p>
        </div>

        <Card className="border border-border/80 bg-card/90 shadow-sm">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-base font-semibold">
              {mode === "signin" ? "Sign in to workspace" : "Create an account"}
            </CardTitle>
            <CardDescription className="text-xs">
              {mode === "signin"
                ? "Enter your corporate credentials to continue."
                : "Register with your authorized corporate email."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-3.5">
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-xs">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    required
                    autoComplete="email"
                    placeholder="analyst@driftwoodcapital.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-8 text-xs h-9"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-xs">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    required
                    minLength={6}
                    autoComplete={mode === "signin" ? "current-password" : "new-password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-8 text-xs h-9"
                  />
                </div>
              </div>

              {error ? (
                <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
                  {error}
                </div>
              ) : null}

              {notice ? (
                <div className="rounded-lg border border-border bg-muted/40 p-2 text-xs text-muted-foreground">
                  {notice}
                </div>
              ) : null}

              <Button
                type="submit"
                className="w-full text-xs h-9 font-medium bg-foreground text-background hover:bg-foreground/90 cursor-pointer shadow-xs"
                disabled={submitting}
              >
                {submitting
                  ? "Authenticating…"
                  : mode === "signin"
                    ? "Sign in"
                    : "Create account"}
              </Button>
            </form>

            <div className="mt-4 text-center text-xs text-muted-foreground">
              {mode === "signin" ? (
                <>
                  Don&apos;t have an account?{" "}
                  <button
                    type="button"
                    onClick={() => switchMode("signup")}
                    className="font-medium text-foreground hover:underline cursor-pointer"
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => switchMode("signin")}
                    className="font-medium text-foreground hover:underline cursor-pointer"
                  >
                    Sign in
                  </button>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}