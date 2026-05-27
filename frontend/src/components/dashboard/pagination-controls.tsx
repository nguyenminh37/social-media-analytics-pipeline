"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";

interface PaginationControlsProps {
  currentPage: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
  isDisabled?: boolean;
  onPageChange: (page: number) => void;
  totalPages: number;
}

function buildVisiblePages(currentPage: number, totalPages: number) {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const startPage = Math.max(1, currentPage - 2);
  const endPage = Math.min(totalPages, startPage + 4);
  const adjustedStartPage = Math.max(1, endPage - 4);

  return Array.from(
    { length: endPage - adjustedStartPage + 1 },
    (_, index) => adjustedStartPage + index,
  );
}

export function PaginationControls({
  currentPage,
  hasNextPage,
  hasPreviousPage,
  isDisabled,
  onPageChange,
  totalPages,
}: PaginationControlsProps) {
  if (totalPages <= 1) {
    return null;
  }

  const visiblePages = buildVisiblePages(currentPage, totalPages);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        disabled={isDisabled || !hasPreviousPage}
        onClick={() => onPageChange(Math.max(currentPage - 1, 1))}
        size="sm"
        variant="outline"
      >
        <ChevronLeft className="size-4" />
        Prev
      </Button>

      {visiblePages.map((page) => (
        <Button
          key={page}
          disabled={isDisabled || page === currentPage}
          onClick={() => onPageChange(page)}
          size="sm"
          variant={page === currentPage ? "default" : "outline"}
        >
          {page}
        </Button>
      ))}

      <Button
        disabled={isDisabled || !hasNextPage}
        onClick={() => onPageChange(currentPage + 1)}
        size="sm"
        variant="outline"
      >
        Next
        <ChevronRight className="size-4" />
      </Button>
    </div>
  );
}
