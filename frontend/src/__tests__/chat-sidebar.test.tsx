import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { ChatSidebar } from "@/components/chat/chat-sidebar"

// Mock the api module
vi.mock("@/lib/api", () => ({
  default: {
    post: vi.fn(),
  },
}))

import api from "@/lib/api"

const mockedApi = vi.mocked(api)

function renderChatSidebar(open = true) {
  const onOpenChange = vi.fn()
  render(
    <MemoryRouter>
      <ChatSidebar open={open} onOpenChange={onOpenChange} />
    </MemoryRouter>
  )
  return { onOpenChange }
}

describe("ChatSidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders when open", () => {
    renderChatSidebar(true)

    expect(screen.getByTestId("chat-sidebar")).toBeInTheDocument()
    expect(screen.getByText("Assistent")).toBeInTheDocument()
  })

  it("has chat input and send button", () => {
    renderChatSidebar(true)

    expect(screen.getByTestId("chat-input")).toBeInTheDocument()
    expect(screen.getByTestId("chat-send-button")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Frage stellen...")).toBeInTheDocument()
  })

  it("shows empty state message", () => {
    renderChatSidebar(true)

    expect(
      screen.getByText("Stelle eine Frage zum Verein, z.B.")
    ).toBeInTheDocument()
  })

  it("sends a message and displays response", async () => {
    const user = userEvent.setup()

    mockedApi.post.mockResolvedValueOnce({
      response: "Der Verein hat 42 aktive Mitglieder.",
      tool_used: "MitgliederService.get_member_stats",
    })

    renderChatSidebar(true)

    const input = screen.getByTestId("chat-input")
    await user.type(input, "Wie viele Mitglieder?")
    await user.click(screen.getByTestId("chat-send-button"))

    // User message should appear
    expect(screen.getByText("Wie viele Mitglieder?")).toBeInTheDocument()

    // Wait for the assistant response
    await waitFor(() => {
      expect(
        screen.getByText("Der Verein hat 42 aktive Mitglieder.")
      ).toBeInTheDocument()
    })

    // Verify API was called
    expect(mockedApi.post).toHaveBeenCalledWith("/api/chat", {
      message: "Wie viele Mitglieder?",
      context: "/",
    })
  })

  it("shows error message on API failure", async () => {
    const user = userEvent.setup()

    mockedApi.post.mockRejectedValueOnce(new Error("Network error"))

    renderChatSidebar(true)

    const input = screen.getByTestId("chat-input")
    await user.type(input, "Test")
    await user.click(screen.getByTestId("chat-send-button"))

    await waitFor(() => {
      expect(
        screen.getByText(/Entschuldigung, es gab einen Fehler/)
      ).toBeInTheDocument()
    })
  })

  it("applies translate-x-full class when closed", () => {
    renderChatSidebar(false)

    const sidebar = screen.getByTestId("chat-sidebar")
    expect(sidebar.className).toContain("translate-x-full")
  })

  it("calls onOpenChange when close button is clicked", async () => {
    const user = userEvent.setup()
    const { onOpenChange } = renderChatSidebar(true)

    await user.click(screen.getByLabelText("Chat schließen"))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
